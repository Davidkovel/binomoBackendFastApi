from typing import Annotated

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, Response, status, Body, Depends
from fastapi.responses import JSONResponse
from fastapi.security.oauth2 import OAuth2PasswordBearer

from app.core.exceptions import EmailAlreadyExistsError, InvalidCredentialsError
from app.interactors.auth import (
    SignInUserInteractor,
    SignUpUserInteractor, OAuth2PasswordBearerUserInteractor
)
from app.schemas.error import ErrorResponse
from app.schemas.user import UserLogin, UserRegister

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

router = APIRouter(route_class=DishkaRoute)


@router.post("/user/auth/sign-up", tags=["B2C"])
async def user_sign_up(
        schema: UserRegister,
        auth_interactor: FromDishka[SignUpUserInteractor],
) -> Response:
    try:
        if schema is None:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=ErrorResponse(message="Request body is required").dict(),
            )

        token = await auth_interactor(user_register=schema)
    except EmailAlreadyExistsError as exc:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=ErrorResponse(message=exc.detail).dict(),
        )

    return JSONResponse(status_code=status.HTTP_200_OK, content={"token": token})


@router.post("/user/auth/sign-in", tags=["B2C"])
async def user_sign_in(
        schema: UserLogin,
        auth_interactor: FromDishka[SignInUserInteractor]
) -> Response:
    try:
        token = await auth_interactor(user_login=schema)
    except InvalidCredentialsError as exc:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content=ErrorResponse(message=exc.detail).dict(),
        )

    return JSONResponse(status_code=status.HTTP_200_OK, content={"token": token})


@router.get("/user/profile/me", tags=["B2C"])
async def user_get_profile(token: Annotated[str, Depends(oauth2_scheme)],
                           oauth2_interactor: FromDishka[OAuth2PasswordBearerUserInteractor]):
    try:
        sub_data = await oauth2_interactor(token)
        user_id = sub_data["user_id"]
        user_email = sub_data["email"]

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "success",
                "user_id": user_id,
                "email": user_email
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": f"500 INTERNAL SERVER ERROR: {str(e)}"}
        )
