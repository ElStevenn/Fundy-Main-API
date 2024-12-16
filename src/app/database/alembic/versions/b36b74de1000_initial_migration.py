"""Initial migration

Revision ID: b36b74de1000
Revises: 
Create Date: 2024-11-21 19:27:59.053010

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b36b74de1000'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('future_cryptos',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('symbol', sa.String(length=255), nullable=False),
    sa.Column('funding_rate_coundown_every', sa.Integer(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('users',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('username', sa.String(length=255), nullable=True),
    sa.Column('name', sa.String(length=255), nullable=True),
    sa.Column('surname', sa.String(length=255), nullable=True),
    sa.Column('email', sa.String(length=255), nullable=True),
    sa.Column('role', sa.String(length=20), nullable=True),
    sa.Column('joined_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('url_picture', sa.String(length=255), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('accounts',
    sa.Column('account_id', sa.String(length=255), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('type', sa.String(length=255), nullable=True),
    sa.Column('email', sa.String(length=255), nullable=True),
    sa.Column('proxy_ip', sa.String(length=255), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('account_id')
    )
    op.create_table('crypto_historical_pnl',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('crypto_id', sa.UUID(), nullable=False),
    sa.Column('avg_entry_price', sa.Numeric(), nullable=False),
    sa.Column('avg_close_price', sa.Numeric(), nullable=False),
    sa.Column('percentage_earning', sa.String(length=255), nullable=True),
    sa.ForeignKeyConstraint(['crypto_id'], ['future_cryptos.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('google_oauth',
    sa.Column('id', sa.String(length=255), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('access_token', sa.Text(), nullable=True),
    sa.Column('refresh_token', sa.Text(), nullable=True),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('historical_searched_cryptos',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('searched_symbol', sa.Text(), nullable=True),
    sa.Column('name', sa.Text(), nullable=True),
    sa.Column('picture_url', sa.Text(), nullable=True),
    sa.Column('searchet_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('monthly_subscription',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('subscription_date', sa.DateTime(timezone=True), nullable=True),
    sa.Column('amount', sa.Float(), nullable=True),
    sa.Column('status', sa.String(length=255), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('starred_cryptos',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('symbol', sa.Text(), nullable=True),
    sa.Column('name', sa.Text(), nullable=True),
    sa.Column('picture_url', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('user_configuration',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('client_timezone', sa.Text(), nullable=True),
    sa.Column('min_funding_rate_threshold', sa.Float(), nullable=True),
    sa.Column('location', sa.Text(), nullable=True),
    sa.Column('bio', sa.Text(), nullable=True),
    sa.Column('webpage_url', sa.Text(), nullable=True),
    sa.Column('oauth_synced', sa.Boolean(), nullable=True),
    sa.Column('picture_synced', sa.Boolean(), nullable=True),
    sa.Column('trading_experience', sa.String(length=20), nullable=True),
    sa.Column('main_used_exchange', sa.Text(), nullable=True),
    sa.Column('public_email', sa.String(length=255), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('historical_pnl',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('avg_entry_price', sa.String(length=255), nullable=True),
    sa.Column('side', sa.String(length=10), nullable=False),
    sa.Column('pnl', sa.Float(), nullable=False),
    sa.Column('net_profits', sa.Float(), nullable=False),
    sa.Column('opening_fee', sa.Float(), nullable=True),
    sa.Column('closing_fee', sa.Float(), nullable=True),
    sa.Column('closed_value', sa.Float(), nullable=False),
    sa.Column('account_id', sa.String(length=255), nullable=False),
    sa.ForeignKeyConstraint(['account_id'], ['accounts.account_id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('risk_management',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('account_id', sa.String(length=255), nullable=False),
    sa.Column('max_drawdown', sa.Float(), nullable=True),
    sa.Column('position_size_limit', sa.Float(), nullable=True),
    sa.Column('leverage_limit', sa.Float(), nullable=True),
    sa.Column('stop_loss', sa.Float(), nullable=True),
    sa.Column('take_profit', sa.Float(), nullable=True),
    sa.Column('daily_loss_limit', sa.Float(), nullable=True),
    sa.ForeignKeyConstraint(['account_id'], ['accounts.account_id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('user_credentials',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('account_id', sa.String(length=255), nullable=False),
    sa.Column('encrypted_apikey', sa.LargeBinary(), nullable=False),
    sa.Column('encrypted_secret_key', sa.LargeBinary(), nullable=False),
    sa.Column('encrypted_passphrase', sa.LargeBinary(), nullable=False),
    sa.ForeignKeyConstraint(['account_id'], ['accounts.account_id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('user_credentials')
    op.drop_table('risk_management')
    op.drop_table('historical_pnl')
    op.drop_table('user_configuration')
    op.drop_table('starred_cryptos')
    op.drop_table('monthly_subscription')
    op.drop_table('historical_searched_cryptos')
    op.drop_table('google_oauth')
    op.drop_table('crypto_historical_pnl')
    op.drop_table('accounts')
    op.drop_table('users')
    op.drop_table('future_cryptos')
    # ### end Alembic commands ###