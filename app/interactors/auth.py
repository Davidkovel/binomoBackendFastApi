from typing import Dict, Tuple

from app.core.exceptions import (
    EmailAlreadyExistsError,
    EntityUnauthorizedError,
    InvalidCredentialsError,
)
from app.core.security import Security
from app.database.repositories.user import UserRepository
from app.database.repositories.PromoCodeRepository import PromoCodeRepository
from app.schemas.user import UserLogin, UserRegister


class SignUpUserInteractor:
    def __init__(self, user_repository: UserRepository, security: Security, promo_repo: PromoCodeRepository):
        self.user_repository = user_repository
        self.promo_repo = promo_repo
        self.security = security

    async def __call__(self, user_register: UserRegister) -> Tuple[str, dict]:
        exist_user = await self.user_repository.get_user_by_email(user_register.email)
        if exist_user:
            raise EmailAlreadyExistsError

        promo_bonus_percent = 0
        promo_code_valid = None

        if user_register.promo_code:
            validation = await self.promo_repo.validate_promo_code(user_register.promo_code)
            if validation["valid"]:
                promo_bonus_percent = validation["bonus_percent"]
                promo_code_valid = user_register.promo_code

        if promo_code_valid:
            await self.promo_repo.increment_promo_usage(promo_code_valid)

        new_user = await self.user_repository.create_new_user(user_register, self.security, promo_code=promo_code_valid,
                                                              promo_bonus_percent=promo_bonus_percent)

        # Создаём JWT-токен, включая ID и email
        token_data = {
            "sub": str(new_user.id),
            "email": new_user.email
        }
        token = self.security.create_access_token(token_data)

        user_data = {
            "user_id": new_user.id,
            "name": new_user.name,
            "email": new_user.email,
            "promo_code": promo_code_valid
        }

        return token, user_data


class SignInUserInteractor:
    def __init__(self, user_repository: UserRepository, security: Security):
        self.user_repository = user_repository
        self.security = security

    async def __call__(self, user_login: UserLogin) -> str:
        user = await self.user_repository.get_user_by_email(user_login.email)
        if not user:
            raise InvalidCredentialsError

        if not self.security.verify_password(user_login.password, user.password):
            raise InvalidCredentialsError

        token_data = {
            "sub": str(user.id),
            "email": user.email
        }
        token = self.security.create_access_token(token_data)

        return token


class OAuth2PasswordBearerUserInteractor:
    def __init__(self, security: Security):
        self.security = security

    async def __call__(self, token: str) -> Dict[str, str]:
        """Returning user id"""

        decoded_token = self.security.decode_access_token(token)
        if not decoded_token:
            raise EntityUnauthorizedError

        user_id = decoded_token.get("sub")
        email = decoded_token.get("email")

        if not user_id or not email:
            raise EntityUnauthorizedError

        return {"user_id": user_id, "email": email}
