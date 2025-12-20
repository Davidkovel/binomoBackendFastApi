from collections.abc import AsyncIterable

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

from app.database.postgres.base import Base


async def create_engine(DB_URI: str) -> AsyncIterable[AsyncSession]:
    engine = create_async_engine(
        url=DB_URI,
        echo=False,
        future=True,

        # 🔥 КРИТИЧНО: Проверяет соединение перед каждым использованием
        # Если соединение разорвано - автоматически создаст новое
        pool_pre_ping=True,

        # 🔄 Автоматически пересоздаёт старые соединения (в секундах)
        # Предотвращает использование "протухших" соединений
        pool_recycle=3600,  # 1 час

        # 📊 Настройки пула соединений
        pool_size=5,  # Сколько соединений держать открытыми
        max_overflow=10,  # Максимум дополнительных соединений при нагрузке
        pool_timeout=30,  # Сколько ждать свободное соединение

        # ⏱️ Таймауты для asyncpg (предотвращают зависание)
        connect_args={
            "timeout": 10,  # Таймаут подключения к БД
            "command_timeout": 60,  # Таймаут выполнения SQL команд
            "server_settings": {
                "application_name": "binomo_backend"  # Имя в pg_stat_activity
            }
        }
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine
    await engine.dispose()


async def create_all_tables(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db(engine: AsyncEngine) -> AsyncIterable[AsyncSession]:
    async with AsyncSession(bind=engine, expire_on_commit=False, autocommit=False, autoflush=False) as db_session:
        yield db_session
