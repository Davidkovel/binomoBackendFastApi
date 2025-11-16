from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.schemas.error import ErrorResponse


class InvalidRequestDataError(Exception):
    def __init__(self, detail="Error en los datos de la solicitud."):
        self.detail = detail
        super().__init__(self.detail)


class InvalidCredentialsError(Exception):
    def __init__(self, detail="Correo electrónico o contraseña incorrectos."):
        self.detail = detail
        super().__init__(self.detail)


class EmailAlreadyExistsError(Exception):
    def __init__(self, detail="Este correo electrónico ya está registrado."):
        self.detail = detail
        super().__init__(self.detail)


class EntityUnauthorizedError(Exception):
    def __init__(self, detail="No hay suficientes fondos"):
        self.detail = detail
        super().__init__(self.detail)


class InsufficientBalanceError(Exception):
    def __init__(self, detail="No hay suficientes fondos."):
        self.detail = detail
        super().__init__(self.detail)


class EntityNotFoundError(Exception):
    def __init__(self, detail="No se ha encontrado el objeto."):
        self.detail = detail
        super().__init__(self.detail)


class EntityAccessDeniedError(Exception):
    def __init__(self, detail="Acceso prohibido"):
        self.detail = detail
        super().__init__(self.detail)


class InsufficientFundsError(Exception):
    def __init__(self, detail="No hay suficientes fondos"):
        self.detail = detail
        super().__init__(self.detail)


async def validation_exception_handler(request: Request, exc: ValidationError):
    for err in exc.errors():
        if "password" in err.get("loc", []):
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "message": "Contraseña débil. Debe tener al menos 6 caracteres e incluir al menos un número. Ejemplo de contraseña segura: qwerty1"}
            )
    # Для остальных ошибок
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"message": "Bad request 400"}
    )


def setup_exception_handlers(app: FastAPI):
    app.add_exception_handler(ValidationError, validation_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(InvalidRequestDataError, validation_exception_handler)
