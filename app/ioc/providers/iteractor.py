from dishka import Provider, Scope, provide, provide_all

from app.database.repositories.moneyRepository import MoneyRepository
from app.interactors.auth import (
    OAuth2PasswordBearerUserInteractor,
    SignInUserInteractor,
    SignUpUserInteractor,
)
from app.interactors.cardIteractor import CardIteractor
from app.interactors.moneyIteractor import MoneyIteractor
from app.interactors.positionHistory import PositionHistoryInteractor
from app.interactors.telegramIteractor import TelegramInteractor


class InteractorProvider(Provider):
    scope = Scope.REQUEST

    auth_interactor = provide_all(
        SignUpUserInteractor,
        SignInUserInteractor,
    )

    oauth2_interactor = provide(OAuth2PasswordBearerUserInteractor)

    # # Добавь APP scope для MoneyIteractor
    # @provide(scope=Scope.APP)
    # def get_money_interactor(
    #     self,
    #     money_repository: MoneyRepository
    # ) -> MoneyIteractor:
    #     return MoneyIteractor(money_repository)

    money_iteractor = provide(MoneyIteractor)
    card_interactor = provide(CardIteractor)
    positions_history_interactor = provide(PositionHistoryInteractor)
    # telegram_interactor = provide(TelegramInteractor)