import os
from decimal import Decimal
from typing import Annotated

import aiofiles
from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, Query, status, Depends, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy import select

from app.api.endpoints.public_endoints.auth import oauth2_scheme
from app.core.exceptions import EntityUnauthorizedError, InsufficientBalanceError
from app.database.postgres.models import UserModel
from app.database.repositories import PromoCodeRepository
from app.database.repositories.moneyRepository import MoneyRepository
from app.database.repositories.positionHistory import PositionHistoryRepository
from app.database.repositories.user import UserRepository
from app.interactors.auth import OAuth2PasswordBearerUserInteractor
from app.interactors.cardIteractor import CardIteractor
from app.interactors.moneyIteractor import MoneyIteractor
from app.interactors.positionHistory import PositionHistoryInteractor
from app.schemas.error import ErrorResponse
from app.schemas.user import DepositRequest, UpdateBalanceRequest, InvoiceToTelegramRequest, \
    UpdateBalanceMultiplyRequest, PositionHistorySchema, PromoCodeValidateSchema, DepositWithPromoSchema

from app.interactors.telegramIteractor import TelegramInteractor

router = APIRouter(route_class=DishkaRoute, prefix="/user", tags=["B2C"])


# @router.get("/profile")
# async def get_user_profile(
#     token: Annotated[str, Depends(oauth2_scheme)],
#     user_interactor: FromDishka[GetUserProfileInteractor],
#     oauth2_interactor: FromDishka[OAuth2PasswordBearerUserInteractor],
#     cache_interactor: FromDishka[CacheAccessTokenInteractor],
# ) -> Response:
#     try:
#         user_id = await oauth2_interactor(token, cache_interactor)
#         user = await user_interactor(user_id)
#     except EntityUnauthorizedError as exc:
#         return JSONResponse(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             content=ErrorResponse(message=exc.detail).dict(),
#         )
#
#     return JSONResponse(status_code=status.HTTP_200_OK, content=user)
#
#
# @router.patch("/profile")
# async def patch_user_profile(
#     token: Annotated[str, Depends(oauth2_scheme)],
#     user_interactor: FromDishka[PatchUserByIdInteractor],
#     oauth2_interactor: FromDishka[OAuth2PasswordBearerUserInteractor],
#     cache_interactor: FromDishka[CacheAccessTokenInteractor],
#     user_patch: UserPatch,
# ) -> Response:
#     try:
#         user_id = await oauth2_interactor(token, cache_interactor)
#         user = await user_interactor(user_id, user_patch)
#     except EntityUnauthorizedError as exc:
#         return JSONResponse(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             content=ErrorResponse(message=exc.detail).dict(),
#         )
#
#     return JSONResponse(status_code=status.HTTP_200_OK, content=user)


@router.get("/get_balance")
async def get_balance(token: Annotated[str, Depends(oauth2_scheme)],
                      money_iteractor: FromDishka[MoneyIteractor],
                      oauth2_interactor: FromDishka[OAuth2PasswordBearerUserInteractor]):
    try:
        sub_data = await oauth2_interactor(token)
        user_id = sub_data["user_id"]

        balance = await money_iteractor.get_user_balance(user_id)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "ok",
                "balance": float(balance.balance)
            }
        )

    except EntityUnauthorizedError as exc:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content=ErrorResponse(message=exc.detail).dict(),
        )


@router.post("/deposit_balance")
async def deposit_balance(token: Annotated[str, Depends(oauth2_scheme)],
                          schema: DepositRequest,
                          oauth2_interactor: FromDishka[OAuth2PasswordBearerUserInteractor],
                          money_iteractor: FromDishka[MoneyIteractor]):
    try:
        if schema is None:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=ErrorResponse(message="Request body is required").dict(),
            )

        sub_data = await oauth2_interactor(token)
        user_id = sub_data["user_id"]

        new_balance = await money_iteractor.make_deposit(user_id, schema.amount)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "ok",
                "balance": float(new_balance.balance)  # ← ИСПРАВЛЕНИЕ
            }
        )

    except EntityUnauthorizedError as exc:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content=ErrorResponse(message=exc.detail).dict(),
        )


@router.post("/update_balance_multiply")
async def update_balance(
        token: Annotated[str, Depends(oauth2_scheme)],
        schema: UpdateBalanceMultiplyRequest,
        oauth2_interactor: FromDishka[OAuth2PasswordBearerUserInteractor],
        money_interactor: FromDishka[MoneyIteractor]
):
    try:
        if schema is None:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=ErrorResponse(message="Request body is required").dict(),
            )

        sub_data = await oauth2_interactor(token)
        user_id = sub_data["user_id"]

        balance = await money_interactor.multiply_money(user_id, schema.multiply_times)
        new_balance = await money_interactor.set_user_balance(
            user_id,
            Decimal(str(balance))
        )

        print(float(new_balance.balance))
        print(float(schema.amount_change))
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "ok",
                "balance": float(new_balance.balance),
                "change": float(schema.amount_change)
            }
        )

    except EntityUnauthorizedError as exc:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content=ErrorResponse(message=exc.detail).dict(),
        )
    except InsufficientBalanceError as exc:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=ErrorResponse(message=exc.detail).dict(),
        )


@router.post("/update_balance")
async def update_balance(
        token: Annotated[str, Depends(oauth2_scheme)],
        schema: UpdateBalanceRequest,
        oauth2_interactor: FromDishka[OAuth2PasswordBearerUserInteractor],
        money_interactor: FromDishka[MoneyIteractor]
):
    try:
        if schema is None:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=ErrorResponse(message="Request body is required").dict(),
            )

        sub_data = await oauth2_interactor(token)
        user_id = sub_data["user_id"]

        new_balance = await money_interactor.set_user_balance(
            user_id,
            Decimal(str(schema.amount_change))
        )

        print(float(new_balance.balance))
        print(float(schema.amount_change))
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "ok",
                "balance": float(new_balance.balance),
                "change": float(schema.amount_change)
            }
        )

    except EntityUnauthorizedError as exc:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content=ErrorResponse(message=exc.detail).dict(),
        )
    except InsufficientBalanceError as exc:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=ErrorResponse(message=exc.detail).dict(),
        )


@router.post("/send_invoice_to_tg")
async def send_invoice_to_tg(
        background_tasks: BackgroundTasks,
        token: Annotated[str, Depends(oauth2_scheme)],
        oauth2_interactor: FromDishka[OAuth2PasswordBearerUserInteractor],
        telegram_interactor: FromDishka[TelegramInteractor],  # Инжектим через Dishka
        invoice_file: UploadFile = File(...),
        amount: str = Form(...)
):
    try:
        sub_data = await oauth2_interactor(token)
        user_id = sub_data["user_id"]
        email = sub_data["email"]

        # Валидация файла
        if not invoice_file.content_type.startswith(('image/', 'application/pdf')):
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"message": "Fayl rasm yoki PDF formatida bo‘lishi kerak"}
            )

        file_path = f"/tmp/{user_id}_{invoice_file.filename}"
        with open(file_path, "wb+") as file_object:
            file_object.write(await invoice_file.read())

        # Запускаем отправку в background
        background_tasks.add_task(
            send_invoice_background,
            telegram_interactor=telegram_interactor,
            user_id=str(user_id),
            email=email,
            amount=Decimal(amount),
            file_path=file_path
        )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "success",
                "message": "Chek muvaffaqiyatli tarzda administratorga yuborildi"
            }
        )
    except EntityUnauthorizedError as exc:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"message": exc.detail},
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": f"Внутренняя ошибка сервера: {str(e)}"}
        )

async def send_invoice_background(telegram_interactor, user_id, email, amount, file_path):
    try:
        await telegram_interactor.send_invoice_notification(
            user_id=user_id,
            user_email=email,
            amount=amount,
            file_path=file_path
        )
    finally:
        # Удаляем временный файл в любом случае
        import os
        if os.path.exists(file_path):
            os.remove(file_path)


@router.get("/get_positions")
async def get_positions(
        token: Annotated[str, Depends(oauth2_scheme)],
        oauth_user: FromDishka[OAuth2PasswordBearerUserInteractor],
        position_repo: FromDishka[PositionHistoryRepository],
):
    try:
        sub_data = await oauth_user(token)
        user_id = sub_data["user_id"]
        email = sub_data["email"]

        positions = await position_repo.get_positions_for_user(user_id)

        return positions

    except Exception as ex:
        return JSONResponse(
            status_code=500,
            content={"message": f"Server error: {str(ex)}"}
        )


@router.post("/validate_promo_code", tags=["Promo"])
async def validate_promo_code(
        schema: PromoCodeValidateSchema,
        token: Annotated[str, Depends(oauth2_scheme)],
        oauth_user: FromDishka[OAuth2PasswordBearerUserInteractor],
        promo_repo: FromDishka[PromoCodeRepository]
):
    """Проверить валидность промокода"""
    try:
        sub_data = await oauth_user(token)
        user_id = sub_data["user_id"]

        # Проверяем не использовал ли уже
        if await promo_repo.check_user_promo_usage(user_id):
            return JSONResponse(
                status_code=400,
                content={"valid": False, "error": "Ya has usado un código promocional"}
            )

        # Валидируем код
        validation = await promo_repo.validate_promo_code(schema.code)

        return JSONResponse(
            status_code=200,
            content=validation
        )

    except Exception as ex:
        return JSONResponse(
            status_code=500,
            content={"error": str(ex)}
        )


@router.post("/deposit_with_promo", tags=["Promo"])
async def deposit_with_promo(
        schema: DepositWithPromoSchema,
        token: Annotated[str, Depends(oauth2_scheme)],
        oauth_user: FromDishka[OAuth2PasswordBearerUserInteractor],
        promo_repo: FromDishka[PromoCodeRepository],
        money_repo: FromDishka[MoneyRepository]
):
    """Депозит с промокодом (включая бонус при регистрации)"""
    try:
        sub_data = await oauth_user(token)
        user_id = sub_data["user_id"]
        base_amount = schema.amount

        # 🔹 Проверяем есть ли промокод при регистрации
        query = select(UserModel).where(UserModel.id == user_id)
        result = await promo_repo.db_session.execute(query)
        user = result.scalar_one_or_none()

        # 🔹 Если у пользователя есть промокод при регистрации и он еще не получал бонус
        if user and user.promo_code_used and user.promo_bonus_received == 0:
            result = await promo_repo.apply_registration_promo(
                user_id=user_id,
                promo_code=user.promo_code_used,
                deposit_amount=base_amount
            )

            if result["success"]:
                final_amount = Decimal(str(result["total_amount"]))
                new_balance = await money_repo.deposit_money(user_id, final_amount)

                return JSONResponse(
                    status_code=200,
                    content={
                        "message": "¡Depósito exitoso! Bonificación de registro aplicada",
                        "base_amount": float(base_amount),
                        "bonus_percent": result["bonus_percent"],
                        "bonus_amount": result["bonus_amount"],
                        "total_deposited": result["total_amount"],
                        "new_balance": float(new_balance),
                        "registration_bonus": True
                    }
                )

        # 🔹 Обычный депозит (если промокод в запросе)
        if schema.promo_code:
            result = await promo_repo.apply_promo_code(
                user_id=user_id,
                promo_code=schema.promo_code,
                deposit_amount=base_amount
            )

            if not result["success"]:
                return JSONResponse(
                    status_code=400,
                    content={"error": result["error"]}
                )

            final_amount = Decimal(str(result["total_amount"]))
            new_balance = await money_repo.deposit_money(user_id, final_amount)

            return JSONResponse(
                status_code=200,
                content={
                    "message": "Depósito exitoso con bonificación",
                    "base_amount": float(base_amount),
                    "bonus_percent": result["bonus_percent"],
                    "bonus_amount": result["bonus_amount"],
                    "total_deposited": result["total_amount"],
                    "new_balance": float(new_balance)
                }
            )
        else:
            # Обычный депозит без промокода
            new_balance = await money_repo.deposit_money(user_id, base_amount)

            return JSONResponse(
                status_code=200,
                content={
                    "message": "Depósito exitoso",
                    "deposited": float(base_amount),
                    "new_balance": float(new_balance)
                }
            )

    except Exception as ex:
        return JSONResponse(
            status_code=500,
            content={"error": str(ex)}
        )




@router.post("/save_position_history")
async def save_position_history(
        schema: PositionHistorySchema,
        token: Annotated[str, Depends(oauth2_scheme)],
        oauth_user: FromDishka[OAuth2PasswordBearerUserInteractor],
        position_history_interactor: FromDishka[PositionHistoryInteractor]
):
    try:
        sub_data = await oauth_user(token)
        user_id = sub_data["user_id"]
        email = sub_data["email"]

        print(schema)
        saved = await position_history_interactor.save_position(user_id, schema)
        print(saved)

        return JSONResponse(
            status_code=200,
            content={"message": "Position saved", "id": str(saved.id)}
        )

    except Exception as ex:
        return JSONResponse(
            status_code=500,
            content={"message": f"Server error: {str(ex)}"}
        )

@router.get("/card_number")
async def get_card_number_for_payment(
        card_interactor: FromDishka[CardIteractor]
):
    try:
        card_response = await card_interactor.get_bank_card()

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "success",
                "card_number": card_response.card_number,
                "card_holder_name": card_response.card_holder_name,
                "bank": card_response.bank
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": f"Внутренняя ошибка сервера: {str(e)}"}
        )


@router.post("/send_withdraw_to_tg")
async def send_withdraw_to_tg(
        token: Annotated[str, Depends(oauth2_scheme)],
        oauth2_interactor: FromDishka[OAuth2PasswordBearerUserInteractor],
        telegram_interactor: FromDishka[TelegramInteractor],  # Инжектим через Dishka
        background_tasks: BackgroundTasks,
        invoice_file: UploadFile = File(...),
        card_number: str = Form(...),
        amount: str = Form(...),
        full_name: str = Form(...),
):
    try:
        sub_data = await oauth2_interactor(token)
        user_id = sub_data["user_id"]
        email = sub_data["email"]

        # Валидация файла
        if not invoice_file.content_type.startswith(('image/', 'application/pdf')):
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"message": "Fayl rasm yoki PDF formatida bo‘lishi kerak"}
            )

        file_path = f"/tmp/{user_id}_{invoice_file.filename}"
        with open(file_path, "wb+") as file_object:
            file_object.write(await invoice_file.read())

        async def process_withdrawal():
            try:
                await telegram_interactor.send_withdraw_notification(
                    user_id=str(user_id),
                    user_email=email,
                    amount=Decimal(amount),
                    file_path=file_path,
                    card_number=card_number,
                    full_name=full_name
                )
            finally:
                if os.path.exists(file_path):
                    os.remove(file_path)

        # Добавляем задачу в фон
        background_tasks.add_task(process_withdrawal)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "success",
                "message": "So‘rov muvaffaqiyatli tarzda administratorga yuborildi"
            }
        )

    except EntityUnauthorizedError as exc:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"message": exc.detail},
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": f"Внутренняя ошибка сервера: {str(e)}"}
        )


# app/api/endpoints/user.py
@router.get("/get_initial_deposit")
async def get_initial_deposit(
        token: Annotated[str, Depends(oauth2_scheme)],
        oauth2_interactor: FromDishka[OAuth2PasswordBearerUserInteractor],
        money_interactor: FromDishka[MoneyIteractor]
):
    try:
        sub_data = await oauth2_interactor(token)
        user_id = sub_data["user_id"]

        initial_deposit = await money_interactor.get_initial_balance(user_id)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "ok",
                "initial_deposit": float(initial_deposit)
            }
        )

    except EntityUnauthorizedError as exc:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content=ErrorResponse(message=exc.detail).dict(),
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse(message=str(e)).dict(),
        )
