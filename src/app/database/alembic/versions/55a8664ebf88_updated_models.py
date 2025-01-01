"""Updated models

Revision ID: 55a8664ebf88
Revises: 0e4a9a2ec7e8
Create Date: 2024-12-31 12:42:41.405610

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '55a8664ebf88'
down_revision: Union[str, None] = '0e4a9a2ec7e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('balance_account_history',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('account_id', sa.String(length=255), nullable=False),
    sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
    sa.Column('asset', sa.String(length=255), nullable=False),
    sa.Column('balance', sa.Float(), nullable=False),
    sa.Column('usd_value', sa.Float(), nullable=False),
    sa.ForeignKeyConstraint(['account_id'], ['accounts.account_id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('balance_account_history')
    # ### end Alembic commands ###
