from sqlalchemy import (Column, Integer, String, ForeignKey)
from sqlalchemy.orm import relationship
from sqlalchemy import ForeignKey
from app.core.database import Base


class Admin(Base):
    __tablename__ = "admins"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        unique=True,
        nullable=False
    )

    nama = Column(
        String(100),
        nullable=False
    )

    user = relationship(
        "User",
        back_populates="admin"
    )