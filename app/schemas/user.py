from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import Field, conint, BaseModel, condecimal, validator

from app.schemas.base import CustomBaseModel
from app.schemas.common import (
    Country,
    Email,
    Password,
    UserFirstName,
)


# class UserTargetSettings(CustomBaseModel):
#     """
#     Таргет настройки пользователя
#     """
#
#     age: conint(ge=0, le=100, strict=True) = Field(
#         ge=0,
#         le=100,
#         strict=True,
#         description="Возраст пользователя",
#         examples=[13],
#     )
#     country: Country


class User(BaseModel):
    """
    Пользователь
    """

    name: UserFirstName
    email: Email


class UserRegister(BaseModel):
    """
    Регистрация пользователя
    """

    name: UserFirstName
    email: Email
    password: Password
    promo_code: Optional[str] = None
    # name: str
    # email: str
    # password: str


class UserLogin(BaseModel):
    """
    Вход пользователя
    """

    email: Email
    password: Password


class UserPatch(BaseModel):
    """
    Обновление данных пользователя
    """

    name: UserFirstName | None = None
    password: Password | None = None


class DepositRequest(BaseModel):
    amount: condecimal(gt=0)


class BalanceResponse(BaseModel):
    balance: Decimal


class BankCardResponse(BaseModel):
    card_number: str

class BankCardAndHolderResponse(BaseModel):
    card_number: str
    card_holder_name: str
    bank: str


class UpdateBalanceMultiplyRequest(BaseModel):
    amount_change: Decimal
    multiply_times: Decimal

class UpdateBalanceRequest(BaseModel):
    amount_change: Decimal


class PositionHistorySchema(BaseModel):
    type: str  # buy / sell / ai
    amount: float
    profit: float
    roi: float

class PromoCodeValidateSchema(BaseModel):
    code: str

    @validator('code')
    def validate_code(cls, v):
        return v.strip().upper()

class DepositWithPromoSchema(BaseModel):
    amount: Decimal
    promo_code: Optional[str] = None

    @validator('promo_code')
    def validate_promo(cls, v):
        if v:
            return v.strip().upper()
        return None

class InvoiceToTelegramRequest(BaseModel):
    amount: Decimal
    # file будет обрабатываться отдельно через FormData


class InvoiceToTelegramResponse(BaseModel):
    status: str
    message: str
    invoice_id: Optional[str] = None

#
# class TransactionHistory(BaseModel):
#     id: UUID
#     user_id: UUID
#     type: str  # 'deposit', 'withdrawal', 'trade'
#     amount: Decimal
#     description: str
#     created_at: datetime
