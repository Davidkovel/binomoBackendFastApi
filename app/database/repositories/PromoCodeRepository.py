from decimal import Decimal

from sqlalchemy import select, update, UUID
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from app.database.postgres.models import PromoCodeModel, UserPromoCodeUsageModel, UserModel


class PromoCodeRepository:
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def get_promo_code(self, code: str):
        """Получить промокод по коду"""
        query = select(PromoCodeModel).where(
            PromoCodeModel.code == code.upper(),
            PromoCodeModel.is_active == True
        )
        result = await self.db_session.execute(query)
        return result.scalar_one_or_none()

    async def validate_promo_code(self, code: str) -> dict:
        """Валидация промокода"""
        promo = await self.get_promo_code(code)

        if not promo:
            return {"valid": False, "error": "Código promocional no válido"}

        if promo.expires_at and promo.expires_at < datetime.utcnow():
            return {"valid": False, "error": "El código promocional ha expirado"}

        if promo.max_uses and promo.current_uses >= promo.max_uses:
            return {"valid": False, "error": "El código ha alcanzado el límite de usos"}

        return {
            "valid": True,
            "bonus_percent": promo.bonus_percent,
            "promo_id": promo.id
        }

    async def check_user_promo_usage(self, user_id: UUID) -> bool:
        """Проверить использовал ли пользователь промокод"""
        query = select(UserModel.promo_code_used).where(UserModel.id == user_id)
        result = await self.db_session.execute(query)
        promo_used = result.scalar_one_or_none()
        return promo_used is not None

    async def increment_promo_usage(self, code: str):
        """Увеличить счетчик использований"""
        query = (
            update(PromoCodeModel)
            .where(PromoCodeModel.code == code.upper())
            .values(current_uses=PromoCodeModel.current_uses + 1)
        )
        await self.db_session.execute(query)
        await self.db_session.commit()

    async def apply_registration_promo(
        self,
        user_id: UUID,
        promo_code: str,
        deposit_amount: Decimal
    ) -> dict:
        """
        Применить промокод при первом депозите после регистрации
        """
        # Получаем пользователя
        query = select(UserModel).where(UserModel.id == user_id)
        result = await self.db_session.execute(query)
        user = result.scalar_one_or_none()

        if not user:
            return {"success": False, "error": "Usuario no encontrado"}

        # Проверяем есть ли сохраненный промокод при регистрации
        if not user.promo_code_used or user.promo_code_used != promo_code.upper():
            return {"success": False, "error": "Este código no coincide con tu registro"}

        # Проверяем не получал ли уже бонус
        if user.promo_bonus_received > 0:
            return {"success": False, "error": "Ya has recibido tu bonificación de registro"}

        # Рассчитываем бонус
        bonus_percent = user.registration_promo_percent or 0
        bonus_amount = (deposit_amount * bonus_percent) / 100
        total_amount = deposit_amount + bonus_amount

        # Сохраняем что бонус был получен
        await self.db_session.execute(
            update(UserModel)
            .where(UserModel.id == user_id)
            .values(promo_bonus_received=bonus_amount)
        )

        # Записываем в историю использования
        promo = await self.get_promo_code(promo_code)
        if promo:
            usage = UserPromoCodeUsageModel(
                user_id=user_id,
                promo_code_id=promo.id,
                bonus_amount=bonus_amount
            )
            self.db_session.add(usage)

        await self.db_session.commit()

        return {
            "success": True,
            "bonus_percent": bonus_percent,
            "bonus_amount": float(bonus_amount),
            "total_amount": float(total_amount)
        }

    async def create_promo_code(
            self,
            code: str,
            bonus_percent: int,
            max_uses: int = None,
            expires_at: datetime = None
    ):
        """Создать новый промокод"""
        promo = PromoCodeModel(
            code=code.upper(),
            bonus_percent=bonus_percent,
            max_uses=max_uses,
            expires_at=expires_at,
            is_active=True,
            current_uses=0
        )
        self.db_session.add(promo)

        try:
            await self.db_session.commit()
            await self.db_session.refresh(promo)
            return promo
        except Exception as e:
            await self.db_session.rollback()
            raise e


    async def apply_promo_to_deposit(
        self,
        user_id: UUID,
        deposit_amount: Decimal
    ) -> dict:
        """
        Применить промокод к депозиту если возможно
        Возвращает финальную сумму и информацию о бонусе
        """
        # Получаем пользователя
        query = select(UserModel).where(UserModel.id == user_id)
        result = await self.db_session.execute(query)
        user = result.scalar_one_or_none()

        if not user:
            return {
                "success": False,
                "error": "Usuario no encontrado",
                "final_amount": deposit_amount,
                "bonus_amount": Decimal('0')
            }

        # Проверяем есть ли неиспользованный промокод
        if not user.promo_code_used or user.promo_bonus_received > 0:
            return {
                "success": True,
                "has_promo": False,
                "final_amount": deposit_amount,
                "bonus_amount": Decimal('0'),
                "bonus_percent": 0
            }

        # Рассчитываем бонус
        bonus_percent = user.registration_promo_percent or 0
        bonus_amount = (deposit_amount * bonus_percent) / 100
        final_amount = deposit_amount + bonus_amount

        # Обновляем что бонус получен
        await self.db_session.execute(
            update(UserModel)
            .where(UserModel.id == user_id)
            .values(promo_bonus_received=bonus_amount)
        )
        await self.db_session.commit()

        return {
            "success": True,
            "has_promo": True,
            "promo_code": user.promo_code_used,
            "bonus_percent": bonus_percent,
            "bonus_amount": bonus_amount,
            "final_amount": final_amount,
            "deposit_amount": deposit_amount
        }