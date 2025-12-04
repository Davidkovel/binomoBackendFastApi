from app.database.repositories.cardRepository import CardRepository
from app.schemas.user import BankCardResponse, BankCardAndHolderResponse


class CardIteractor:
    def __init__(self, card_repository: CardRepository):
        self.card_repository = card_repository

    async def get_bank_card(self) -> BankCardAndHolderResponse:
        card_number, card_holder_name, bank = await self.card_repository.get_card_data()

        if card_number is None:
            card_number = "8600 0000 0000 0000"  # дефолтное значение

        if card_holder_name is None:
            card_holder_name = "Card Holder Name"  # дефолтное значение

        return BankCardAndHolderResponse(
            card_number=card_number,
            card_holder_name=card_holder_name,
            bank=bank
        )

    async def set_bank_card(self, card_number: str, card_holder_name: str, bank: str) -> BankCardResponse:
        card_number, card_holder_name, bank = await self.card_repository.set_card_data(
            card_number=card_number,
            card_holder_name=card_holder_name,
            bank=bank
        )

        return BankCardResponse(card_number=card_number)
