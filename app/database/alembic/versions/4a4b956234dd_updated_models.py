"""Updated models

Revision ID: 4a4b956234dd
Revises: 93515436926b
Create Date: 2024-09-19 12:33:13.873603

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4a4b956234dd'
down_revision: Union[str, None] = '93515436926b'
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
    op.create_table('crypto_historical_pnl',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('crypto_id', sa.UUID(), nullable=False),
    sa.Column('avg_entry_price', sa.Numeric(), nullable=False),
    sa.Column('avg_close_price', sa.Numeric(), nullable=False),
    sa.Column('percentage_earning', sa.String(length=255), nullable=True),
    sa.ForeignKeyConstraint(['crypto_id'], ['future_cryptos.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('crypto_historical_pnl')
    op.drop_table('future_cryptos')
    # ### end Alembic commands ###
