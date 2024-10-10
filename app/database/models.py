from sqlalchemy import String, Float, DateTime, Text, ForeignKey, JSON, BIGINT, Column, func, Integer, Numeric, INT, LargeBinary
from sqlalchemy.dialects.postgresql import UUID as pgUUID
from sqlalchemy.orm import relationship, declarative_base
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
from config import PRIVATE_KEY
import uuid

Base = declarative_base()

class Users(Base):
    __tablename__ = "users"

    id = Column(pgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(255))
    name = Column(String(255))
    surname = Column(String(255))
    email = Column(String(255))
    role = Column(String(20), default='user') # 'user', 'moderator', 'administrator'
    joined_at = Column(DateTime(timezone=True), default=func.now())
    url_picture = Column(String(255))

    # One-to-many relationships
    accounts = relationship("Account", back_populates="user", cascade="all, delete-orphan")
    google_oauths = relationship("GoogleOAuth", back_populates="user", cascade="all, delete-orphan")
    user_configurations = relationship("UserConfiguration", back_populates="user", cascade="all, delete-orphan")
    monthly_subscriptions = relationship("MonthlySubscription", back_populates="user", cascade="all, delete-orphan")
    historical_searched_cryptos = relationship("HistoricalSearchedCryptos", back_populates="user", cascade="all, delete-orphan")
    starred_cryptos = relationship("StarredCryptos", back_populates="user", cascade="all, delete-orphan")

class GoogleOAuth(Base):
    __tablename__ = "google_oauth"

    id = Column(String(255), primary_key=True)
    user_id = Column(pgUUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    access_token = Column(Text)
    refresh_token = Column(Text)
    expires_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=func.now())

    # Many-to-one relationship with Users
    user = relationship("Users", back_populates="google_oauths")

class UserConfiguration(Base):
    __tablename__ = "user_configuration"

    id = Column(pgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(pgUUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    client_timezone = Column(Text, default='Europe/Amsterdam')
    minimum_founding_rate_to_show = Column(Float)
    main_used_exchange = Column(Text, default="bitget") # 'bitget', 'binance', 'okx', 'crypto.com', 'kucoin'

    # Many-to-one relationship with Users
    user = relationship("Users", back_populates="user_configurations")

class MonthlySubscription(Base):
    __tablename__ = "monthly_subscription"

    id = Column(pgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(pgUUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    subscription_date = Column(DateTime(timezone=True), default=func.now())
    amount = Column(Float)
    status = Column(String(255))

    # Many-to-one relationship with Users
    user = relationship("Users", back_populates="monthly_subscriptions")

class Account(Base):
    __tablename__ = "accounts"

    id = Column(pgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(pgUUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    type = Column(String(255))
    email = Column(String(255))

    # One-to-many Historical_PNL as UserCredentials
    historical_pnls = relationship("Historical_PNL", back_populates="account", cascade="all, delete-orphan")
    user_credentials = relationship("UserCredentials", back_populates="account", cascade="all, delete-orphan")

    # Many-to-one relationship with Users
    user = relationship("Users", back_populates="accounts")

class Historical_PNL(Base):
    __tablename__ = "historical_pnl"

    id = Column(pgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    avg_entry_price = Column(String(255))
    side = Column(String(10), nullable=False)
    pnl = Column(Float, nullable=False)
    net_profits = Column(Float, nullable=False)
    opening_fee = Column(Float)
    closing_fee = Column(Float)
    closed_value = Column(Float, nullable=False)
    account_id = Column(pgUUID(as_uuid=True), ForeignKey('accounts.id'), nullable=False)

    account = relationship("Account", back_populates="historical_pnls")


class UserCredentials(Base):
    __tablename__ = "user_credentials"

    id = Column(pgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id = Column(pgUUID(as_uuid=True), ForeignKey('accounts.id'), nullable=False)
    encrypted_apikey = Column(LargeBinary, nullable=False)
    encrypted_secret_key = Column(LargeBinary, nullable=False)
    encrypted_passphrase = Column(LargeBinary, nullable=False)

    account = relationship("Account", back_populates="user_credentials")

    # Store the already encrypted API key
    def set_encrypted_apikey(self, encrypted_apikey):
        self.encrypted_apikey = encrypted_apikey

    # Store the already encrypted secret key
    def set_encrypted_secret_key(self, encrypted_secret_key):
        self.encrypted_secret_key = encrypted_secret_key

    # Store the already encrypted passphrase
    def set_encrypted_passphrase(self, encrypted_passphrase):
        self.encrypted_passphrase = encrypted_passphrase

    # Decrypt the API key using the private RSA key
    def get_apikey(self):
        decrypted_apikey = PRIVATE_KEY.decrypt(
            self.encrypted_apikey,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        return decrypted_apikey.decode('utf-8')

    # Decrypt the secret key using the private RSA key
    def get_secret_key(self):
        decrypted_secret_key = PRIVATE_KEY.decrypt(
            self.encrypted_secret_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        return decrypted_secret_key.decode('utf-8')

    # Decrypt the passphrase using the private RSA key
    def get_passphrase(self):
        decrypted_passphrase = PRIVATE_KEY.decrypt(
            self.encrypted_passphrase,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        return decrypted_passphrase.decode('utf-8')


# CRYPTO MODELS
class FutureCryptos(Base):
    __tablename__ = "future_cryptos"

    id = Column(pgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol = Column(String(255), nullable=False)
    funding_rate_coundown_every = Column(Integer, default=8) # 8 or 4

    crypto_historical_pnl = relationship("CryptoHistoricalPNL", back_populates="crypto", cascade="all, delete-orphan")


class CryptoHistoricalPNL(Base):
    __tablename__ = "crypto_historical_pnl"

    id = Column(pgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    crypto_id = Column(pgUUID(as_uuid=True), ForeignKey('future_cryptos.id'), nullable=False)
    avg_entry_price = Column(Numeric, nullable=False)
    avg_close_price = Column(Numeric, nullable=False)
    percentage_earning = Column(String(255))

    crypto = relationship("FutureCryptos", back_populates="crypto_historical_pnl")

class StarredCryptos(Base):
    __tablename__ = "starred_cryptos"

    id = Column(pgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(pgUUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    symbol = Column(Text)
    name = Column(Text)
    picture_url = Column(Text)

    user = relationship("Users", back_populates="starred_cryptos")


# USER HISTORICAL
class HistoricalSearchedCryptos(Base):
    __tablename__ = "historical_searched_cryptos"

    id = Column(pgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(pgUUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    searched_symbol = Column(Text)
    name = Column(Text)
    picture_url = Column(Text)
    searchet_at = Column(DateTime(timezone=True), default=func.now())

    user = relationship("Users", back_populates="historical_searched_cryptos")

    

# MIGRATE MODEL
"""
 - alembic upgrade head
 - alembic revision --autogenerate -m "Updated models"

 | 

  ../../venv/bin/alembic upgrade head
  ../../venv/bin/alembic revision --autogenerate -m "Updated models"

  | 

  ../../venv/bin/python ../../venv/bin/alembic upgrade head
  ../../venv/bin/python ../../venv/bin/alembic revision --autogenerate -m "Updated models"

"""