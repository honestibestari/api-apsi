import enum

from sqlalchemy import Column, Integer, String, Enum, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    MERCHANT = "merchant"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False)
    email = Column(String(150), unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(Enum(UserRole), nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    admin = relationship(
        "Admin",
        back_populates="user",
        uselist=False
    )

    merchant = relationship(
        "Merchant",
        back_populates="user",
        uselist=False
    )