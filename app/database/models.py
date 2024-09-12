from sqlalchemy import String, Float, DateTime, Text, ForeignKey, JSON, INT, Column
from sqlalchemy.dialects.postgresql import UUID as pgUUID
from sqlalchemy.orm import relationship, DeclarativeBase
import uuid

class Base(DeclarativeBase):
    pass

class Users(Base):
    __tablename__ = "users"

    id = Column(pgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(255))

    # One-to-many relationship with Account
    accounts = relationship("Account", back_populates="user", cascade="all, delete-orphan")

class Account(Base):
    __tablename__ = "accounts"

    id = Column(String(255), primary_key=True)
    type = Column(String(255)) # Spot, Futures, Margin...
    email = Column(String(255))

    # Foreign key to reference Users table
    user_id = Column(pgUUID(as_uuid=True), ForeignKey('users.id'), nullable=False)

    # One-to-many relationship with Historical_PNL
    historical_pnls = relationship("Historical_PNL", back_populates="account", cascade="all, delete-orphan")

    # Many-to-one relationship with Users
    user = relationship("Users", back_populates="accounts")

class Historical_PNL(Base):
    __tablename__ = "historical_pnl"

    id = Column(pgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    avg_entry_price = Column(String(255))
    side = Column(String(10), nullable=False) # 'long' or 'short'
    pnl = Column(Float, nullable=False)
    net_profits = Column(Float, nullable=False)
    opening_fee = Column(Float)
    closing_fee = Column(Float)
    closed_value = Column(Float, nullable=False)

    # Foreign key to reference Accounts table
    account_id = Column(String(255), ForeignKey('accounts.id'), nullable=False)

    # Many-to-one relationship with Account
    account = relationship("Account", back_populates="historical_pnls")

# MIGRATE MODEL
"""
 - alembic upgrade head
 - alembic revision --autogenerate -m "Updated models"
"""