from collections.abc import Iterable
from datetime import date
from decimal import Decimal
from typing import Tuple, Optional

from sqlalchemy import and_, func, or_, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.core.exceptions import (
    EntityAccessDeniedError,
    EntityNotFoundError,
    EntityUnauthorizedError, InsufficientFundsError,
)
from app.core.security import Security
from app.database.postgres.models import (
    UserModel,
)
from app.schemas.common import Email, UserId
from app.schemas.user import UserPatch, UserRegister


class UserRepository:
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def create_new_user(self, user: UserRegister, security: Security, promo_code: Optional[str] = None, promo_bonus_percent: int = 0) -> UserModel:
        hashed_password = security.get_password_hash(user.password)
        new_user = UserModel(
            name=user.name,
            email=user.email,
            password=hashed_password,
            promo_code_used=promo_code,  # 🔹 Сохраняем промокод
            registration_promo_percent=promo_bonus_percent  # 🔹 Процент бонуса
        )

        self.db_session.add(new_user)
        await self.db_session.commit()
        await self.db_session.refresh(new_user)

        return new_user

    async def get_user_by_email(self, email: Email) -> UserModel:
        query = select(UserModel).where(UserModel.email == email)
        result = await self.db_session.execute(query)

        return result.scalars().one_or_none()

    async def get_user_by_id(self, user_id: UserId) -> UserModel:
        query = select(UserModel).where(UserModel.id == user_id)
        result = await self.db_session.execute(query)

        return result.scalars().one_or_none()

    async def patch_user_by_id(self, user_id: UserId, user_patch: UserPatch, security: Security) -> UserModel:
        query = select(UserModel).where(UserModel.id == user_id)

        result = await self.db_session.execute(query)
        user = result.scalars().one_or_none()

        if not user:
            raise EntityUnauthorizedError

        if user_patch.name:
            user.name = user_patch.name
        if user_patch.password:
            user.password = security.get_password_hash(user_patch.password)

        await self.db_session.commit()
        await self.db_session.refresh(user)

        return user
