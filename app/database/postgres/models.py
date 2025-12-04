import uuid
from datetime import date, datetime

from sqlalchemy import (
    UUID,
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Table, Numeric,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship

from app.database.postgres.base import Base


class UserModel(Base):
    __tablename__ = "users"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        unique=True,
        nullable=False,
        default=uuid.uuid4,
    )
    name = Column(String(100), nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    balance = Column(Numeric(15, 2), default=0.00, nullable=False)
    initial_balance = Column(Numeric(15, 2), default=0.00, nullable=False)  # 🔹 Добавляем
    has_initial_deposit = Column(Boolean, default=False, nullable=False)  # 🔹 Флаг первого депозита


class BankCardModel(Base):
    __tablename__ = "card"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        unique=True,
        nullable=False,
        default=uuid.uuid4,
    )
    card_number = Column(String(100), default="1111 2222 3333 4444", nullable=False)
    card_holder_name = Column(String(100), )
    bank = Column(String(100), )
