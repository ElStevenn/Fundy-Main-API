from sqlalchemy import String, Float, DateTime, Text, ForeignKey, Column, func, Integer, Numeric, LargeBinary, Boolean
from sqlalchemy.dialects.postgresql import UUID as pgUUID, JSON
from sqlalchemy.orm import relationship, declarative_base
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
from config import PRIVATE_KEY
import uuid
import base64

Base = declarative_base()

class Users(Base):
    __tablename__ = "users"

    id = Column(pgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(255), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    surname = Column(String(255), nullable=True)
    email = Column(String(255), unique=True, nullable=False)
    role = Column(String(20), default='user')
    joined_at = Column(DateTime(timezone=True), default=func.now())
    url_picture = Column(String(255), nullable=True)

    accounts = relationship("Account", back_populates="user", cascade="all, delete-orphan")
    google_oauths = relationship("GoogleOAuth", back_populates="user", cascade="all, delete-orphan")
    historical_searched_cryptos = relationship("HistoricalSearchedCryptos", back_populates="user", cascade="all, delete-orphan")
    starred_cryptos = relationship("StarredCryptos", back_populates="user", cascade="all, delete-orphan")

    user_configurations = relationship("UserConfiguration", back_populates="user", cascade="all, delete-orphan", uselist=False)


class GoogleOAuth(Base):
    __tablename__ = "google_oauth"

    id = Column(String(255), primary_key=True)
    user_id = Column(pgUUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=func.now())

    user = relationship("Users", back_populates="google_oauths")


class UserConfiguration(Base):
    __tablename__ = "user_configuration"

    id = Column(pgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(pgUUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    client_timezone = Column(Text, default='Europe/Amsterdam')
    min_funding_rate_threshold = Column(Float, nullable=True)
    location = Column(Text, nullable=True)
    bio = Column(Text, nullable=True)
    webpage_url = Column(Text, nullable=True)
    oauth_synced = Column(Boolean, default=True)
    picture_synced = Column(Boolean, default=True)
    trading_experience = Column(String(20), default='new')
    main_used_exchange = Column(Text, default="bitget")
    public_email = Column(String(255), nullable=True)

    user = relationship("Users", back_populates="user_configurations")


class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"

    id = Column(pgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(50), unique=True, nullable=False)
    max_linked_accounts = Column(Integer, nullable=False)
    max_bots = Column(Integer, nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    features = Column(JSON, nullable=True)

    # Removed relationship to MonthlySubscription


class Account(Base):
    __tablename__ = "accounts"

    account_id = Column(String(255), primary_key=True)
    user_id = Column(pgUUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    account_name = Column(String(255), nullable=False)
    type = Column(String(255), nullable=False)
    email = Column(String(255), nullable=True)
    proxy_ip = Column(String(255), nullable=True)
    account_permissions = Column(JSON, nullable=True)

    historical_pnls = relationship("Historical_PNL", back_populates="account", cascade="all, delete-orphan")
    user_credentials = relationship("UserCredentials", back_populates="account", cascade="all, delete-orphan")
    bots = relationship("Bot", back_populates="account", cascade="all, delete-orphan")
    spot_history = relationship("SpotHistory", back_populates="account", cascade="all, delete-orphan")
    futures_history = relationship("FuturesHistory", back_populates="account", cascade="all, delete-orphan")
    balance_history = relationship("BalanceAccountHistory", back_populates="account", cascade="all, delete-orphan")

    risk_management = relationship(
        "RiskManagement",
        back_populates="account",
        uselist=False,
        cascade="all, delete-orphan"
    )

    user = relationship("Users", back_populates="accounts")


class Bot(Base):
    __tablename__ = "bots"

    id = Column(pgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id = Column(String(255), ForeignKey('accounts.account_id'), nullable=False)
    name = Column(String(255), nullable=False)
    strategy = Column(String(100), nullable=False)
    status = Column(String(50), default='active')
    profit_loss = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), default=func.now())
    last_run = Column(DateTime(timezone=True), nullable=True)
    configuration = Column(JSON, nullable=True)

    account = relationship("Account", back_populates="bots")
    pnl_history = relationship("BotPNLHistory", back_populates="bot", cascade="all, delete-orphan")
    extra_metadata = Column(JSON, nullable=True)


class BotPNLHistory(Base):
    __tablename__ = "bot_pnl_history"

    id = Column(pgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bot_id = Column(pgUUID(as_uuid=True), ForeignKey('bots.id'), nullable=False)
    timestamp = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    pnl = Column(Float, nullable=False)
    roe = Column(Float, nullable=False)

    bot = relationship("Bot", back_populates="pnl_history")


class Historical_PNL(Base):
    __tablename__ = "historical_pnl"

    id = Column(pgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    avg_entry_price = Column(String(255), nullable=True)
    side = Column(String(10), nullable=False)
    pnl = Column(Float, nullable=False)
    net_profits = Column(Float, nullable=False)
    opening_fee = Column(Float, nullable=True)
    closing_fee = Column(Float, nullable=True)
    closed_value = Column(Float, nullable=False)
    account_id = Column(String(255), ForeignKey('accounts.account_id'), nullable=False)

    account = relationship("Account", back_populates="historical_pnls")


class UserCredentials(Base):
    __tablename__ = "user_credentials"

    id = Column(pgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id = Column(String(255), ForeignKey('accounts.account_id'), nullable=False)
    exchange_name = Column(String(255), nullable=False)
    encrypted_apikey = Column(LargeBinary, nullable=True)
    encrypted_secret_key = Column(LargeBinary, nullable=True)
    encrypted_passphrase = Column(LargeBinary, nullable=True)
    oauth2_token = Column(LargeBinary, nullable=True)

    account = relationship("Account", back_populates="user_credentials")

    def set_encrypted_apikey(self, encrypted_apikey: str):
        self.encrypted_apikey = base64.b64decode(encrypted_apikey.encode('utf-8'))

    def set_encrypted_secret_key(self, encrypted_secret_key: str):
        self.encrypted_secret_key = base64.b64decode(encrypted_secret_key.encode('utf-8'))

    def set_encrypted_passphrase(self, encrypted_passphrase: str):
        self.encrypted_passphrase = base64.b64decode(encrypted_passphrase.encode('utf-8'))

    def set_encrypted_oauth2_token(self, encrypted_oauth2_token: str):
        self.oauth2_token = base64.b64decode(encrypted_oauth2_token.encode('utf-8'))

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

    def get_oauth2_token(self):
        decrypted_oauth2_token = PRIVATE_KEY.decrypt(
            self.oauth2_token,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        return decrypted_oauth2_token.decode('utf-8')


class SpotHistory(Base):
    __tablename__ = "spot_history"

    id = Column(pgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id = Column(String(255), ForeignKey('accounts.account_id'), nullable=False)
    timestamp = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    asset = Column(String(255), nullable=False)
    balance = Column(Float, nullable=False)
    usd_value = Column(Float, nullable=False)

    account = relationship("Account", back_populates="spot_history")


class FuturesHistory(Base):
    __tablename__ = "futures_history"

    id = Column(pgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id = Column(String(255), ForeignKey('accounts.account_id'), nullable=False)
    timestamp = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    asset = Column(String(255), nullable=False)
    balance = Column(Float, nullable=False)
    usd_value = Column(Float, nullable=False)

    account = relationship("Account", back_populates="futures_history")


class BalanceAccountHistory(Base):
    __tablename__ = "balance_account_history"

    id = Column(pgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id = Column(String(255), ForeignKey('accounts.account_id'), nullable=False)
    timestamp = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    asset = Column(String(255), nullable=False)
    balance = Column(Float, nullable=False)
    usd_value = Column(Float, nullable=False)

    account = relationship("Account", back_populates="balance_history")


class RiskManagement(Base):
    __tablename__ = "risk_management"

    id = Column(pgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id = Column(String(255), ForeignKey('accounts.account_id'), nullable=False)

    max_drawdown = Column(Float, nullable=True)
    position_size_limit = Column(Float, nullable=True)
    leverage_limit = Column(Float, default=10.0)
    stop_loss = Column(Float, default=5.0)
    take_profit = Column(Float, default=10.0)
    daily_loss_limit = Column(Float, nullable=True)

    account = relationship("Account", back_populates="risk_management")


class StarredCryptos(Base):
    __tablename__ = "starred_cryptos"

    id = Column(pgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(pgUUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    symbol = Column(Text, nullable=False)
    name = Column(Text, nullable=False)
    picture_url = Column(Text, nullable=True)

    user = relationship("Users", back_populates="starred_cryptos")


class HistoricalSearchedCryptos(Base):
    __tablename__ = "historical_searched_cryptos"

    id = Column(pgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(pgUUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    searched_symbol = Column(Text, nullable=False)
    name = Column(Text, nullable=False)
    picture_url = Column(Text, nullable=True)
    searched_at = Column(DateTime(timezone=True), default=func.now())

    user = relationship("Users", back_populates="historical_searched_cryptos")


# MIGRATE MODEL
"""
 - alembic upgrade head
 - alembic revision --autogenerate -m "Added SubscriptionPlan and Bot models"

 | 

  ../../venv/bin/alembic upgrade head
  ../../venv/bin/alembic revision --autogenerate -m "Added SubscriptionPlan and Bot models"

  | 

  ../../venv/bin/python ../../venv/bin/alembic upgrade head
  ../../venv/bin/python ../../venv/bin/alembic revision --autogenerate -m "Added SubscriptionPlan and Bot models"

"""
