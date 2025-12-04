from typing import List

from dns.e164 import query
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.postgres.models import BankCardModel


class CardRepository:
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    # async def get_card_number(self) -> str:
    #     query = select(BankCardModel.card_number)
    #     result = await self.db_session.execute(query)
    #     card_number = result.scalar_one_or_none()
    #
    #     # Если карты нет в базе, возвращаем дефолтное значение
    #     if card_number is None:
    #         return "8600 0000 0000 0000"  # или любое другое дефолтное значение
    #
    #     return card_number

    async def get_card_data(self) -> tuple[str, str, str]:
        query = select(BankCardModel.card_number, BankCardModel.card_holder_name, BankCardModel.bank)
        result = await self.db_session.execute(query)
        card_data = result.first()

        # Если карты нет в базе, возвращаем дефолтные значения
        if card_data is None:
            return "8600 0000 0000 0000", "Card Holder Name", "Uz bank"

        return card_data[0], card_data[1], card_data[2]

    async def get_card_number(self) -> List[str]:
        card_number, _ = await self.get_card_data()
        return [card_number, _]

    async def get_card_holder_name(self) -> str:
        _, card_holder_name = await self.get_card_data()
        return card_holder_name

    async def get_bank(self) -> str:
        _, _, bank = await self.get_card_data()
        return bank

    async def set_card_data(self, card_number: str, card_holder_name: str, bank: str) -> tuple[str, str, str]:
        # Сначала проверяем, есть ли уже запись
        existing_query = select(BankCardModel)
        existing_result = await self.db_session.execute(existing_query)
        existing_card = existing_result.scalar_one_or_none()

        if existing_card:
            # Обновляем существующую запись
            query = (
                update(BankCardModel)
                .where(BankCardModel.id == existing_card.id)
                .values(
                    card_number=card_number,
                    card_holder_name=card_holder_name,
                    bank=bank
                )
            )
            await self.db_session.execute(query)
        else:
            # Создаем новую запись
            new_card = BankCardModel(
                card_number=card_number,
                card_holder_name=card_holder_name,
                bank=bank
            )
            self.db_session.add(new_card)

        await self.db_session.commit()
        return card_number, card_holder_name,bank

    async def set_card_number(self, card_number: str) -> str:
        current_holder_name = await self.get_card_holder_name()
        card_number, _ = await self.set_card_data(card_number, current_holder_name)
        return card_number

    async def set_card_holder_name(self, holder_name: str) -> str:
        current_card_number = await self.get_card_number()
        _, holder_name = await self.set_card_data(current_card_number, holder_name)
        return holder_name

    async def set_bank(self, bank: str) -> str:
        current_card_number = await self.get_card_number()
        current_holder_name = await self.get_card_holder_name()
        _, _, bank = await self.set_card_data(current_card_number, current_holder_name, bank)
        return bank