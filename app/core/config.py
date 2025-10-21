from dataclasses import dataclass
from os import getenv
from typing import Optional, List

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class PostgresConfig:
    POSTGRES_CONN: str | None
    POSTGRES_JDBC_URL: str | None
    POSTGRES_USERNAME: str | None
    POSTGRES_PASSWORD: str | None
    POSTGRES_HOST: str | None
    POSTGRES_PORT: int | None
    POSTGRES_DATABASE: str | None

    @staticmethod
    def from_env() -> "PostgresConfig":
        conn = getenv("POSTGRES_CONN")
        jdbc = getenv("POSTGRES_JDBC_URL")
        username = getenv("POSTGRES_USERNAME")
        password = getenv("POSTGRES_PASSWORD")
        host = getenv("POSTGRES_HOST")
        port = getenv("POSTGRES_PORT")
        database = getenv("POSTGRES_DATABASE")

        return PostgresConfig(
            POSTGRES_CONN=conn,
            POSTGRES_JDBC_URL=jdbc,
            POSTGRES_USERNAME=username,
            POSTGRES_PASSWORD=password,
            POSTGRES_HOST=host,
            POSTGRES_PORT=port,
            POSTGRES_DATABASE=database,
        )


@dataclass(frozen=True)
class ServerConfig:
    SERVER_ADDRESS: str
    SERVER_PORT: int | None

    @staticmethod
    def from_env() -> "ServerConfig":
        address = getenv("SERVER_ADDRESS", "0.0.0.0")
        port = getenv("SERVER_PORT", 8080)

        return ServerConfig(SERVER_ADDRESS=address, SERVER_PORT=port)


@dataclass(frozen=True)
class SecurityConfig:
    RANDOM_SECRET: str
    ALGORITH: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int

    @staticmethod
    def from_env() -> "SecurityConfig":
        secret = getenv("RANDOM_SECRET")
        algorithm = getenv("ALGORITH", "HS256")
        expire_minutes = getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 3060)

        return SecurityConfig(RANDOM_SECRET=secret, ALGORITH=algorithm, ACCESS_TOKEN_EXPIRE_MINUTES=expire_minutes)


@dataclass(frozen=True)
class AntifraudConfig:
    ANTIFRAUD_ADDRESS: str

    @staticmethod
    def from_env() -> "AntifraudConfig":
        address = getenv("ANTIFRAUD_ADDRESS", "localhost:9090")

        return AntifraudConfig(ANTIFRAUD_ADDRESS=address)


@dataclass(frozen=True)
class TelegramConfig:
    bot_token: str
    chat_ids: List[int]


@dataclass(frozen=True)
class Config:
    postgres_config: PostgresConfig
    server_config: ServerConfig
    auth_token_config: SecurityConfig
    telegram_config: TelegramConfig


def create_config() -> Config:
    return Config(
        postgres_config=PostgresConfig.from_env(),
        server_config=ServerConfig.from_env(),
        auth_token_config=SecurityConfig.from_env(),
        telegram_config=TelegramConfig(
            bot_token="8339016480:AAFj8ZMpw-dNzr65QdEzjITznLvg0SHX_OI",
            chat_ids=[-4970376929]
        )
    )
