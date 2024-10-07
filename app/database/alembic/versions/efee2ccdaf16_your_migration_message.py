"""Your migration message

Revision ID: efee2ccdaf16
Revises: 
Create Date: 2024-09-11 17:04:37.204225

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'efee2ccdaf16'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('users',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('username', sa.String(length=255), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('accounts',
    sa.Column('id', sa.String(length=255), nullable=False),
    sa.Column('type', sa.String(length=255), nullable=True),
    sa.Column('email', sa.String(length=255), nullable=True),
    sa.Column('user_id', sa.UUID(), nullable=False),
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
    sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('historical_pnl')
    op.drop_table('accounts')
    op.drop_table('users')
    # ### end Alembic commands ###