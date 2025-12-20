import contextlib

import uvicorn
from dishka.integrations.fastapi import setup_dishka
from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncEngine

from app.api.endpoints import root_router
from app.core.build import create_async_container
from app.core.config import create_config
from app.core.exceptions import setup_exception_handlers
from app.database.init_db import init_database
from app.database.repositories.PromoCodeRepository import PromoCodeRepository
from app.interactors.promo_init import create_default_promo_codes
from app.interactors.telegramIteractor import TelegramInteractor
from app.ioc.registry import get_providers


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    container = app.state.dishka_container

    # Получаем TelegramInteractor из контейнера
    telegram_interactor = await container.get(TelegramInteractor)

    # ВАЖНО: Устанавливаем контейнер для доступа к зависимостям
    telegram_interactor.set_container(container)
    telegram_interactor.set_container_card(container)
    await telegram_interactor.start_polling()
    print("✅ Application started successfully")

    engine = await container.get(AsyncEngine)

    await init_database(engine)
    print("✅ Database initialized")

    engine = await container.get(AsyncEngine)
    from sqlalchemy.ext.asyncio import AsyncSession

    async with AsyncSession(engine, expire_on_commit=False) as session:
        await create_default_promo_codes(session, PromoCodeRepository)

    print("✅ Promo codes initialized")
    print("✅ Application started successfully")

    yield  # Приложение работает

    # Shutdown
    print("🛑 Shutting down application...")

    # Останавливаем бота
    await telegram_interactor.stop_polling()

    # Закрываем контейнер
    await container.close()

    print("✅ Application shutdown complete")

def create_app() -> FastAPI:
    app = FastAPI(lifespan=lifespan)

    return app


def configure_app(app: FastAPI, root_router: APIRouter) -> None:
    app.include_router(root_router, prefix="/api")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    setup_exception_handlers(app)

    container = create_async_container(get_providers())
    setup_dishka(container, app)


def main():
    app = create_app()
    configure_app(app, root_router)

    config = create_config()

    host = config.server_config.SERVER_ADDRESS
    port = config.server_config.SERVER_PORT

    if ":" in host:
        host, port = host.split(":")

    uvicorn.run(app, host=host, port=int(port))


if __name__ == "__main__":
    main()