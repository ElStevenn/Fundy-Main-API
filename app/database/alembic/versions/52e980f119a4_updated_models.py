"""Updated models

Revision ID: 52e980f119a4
Revises: d92c6818c51f
Create Date: 2024-09-23 15:59:11.930436

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '52e980f119a4'
down_revision: Union[str, None] = 'd92c6818c51f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('google_oauth', 'id',
               existing_type=sa.INTEGER(),
               type_=sa.BIGINT(),
               existing_nullable=False,
               autoincrement=True)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('google_oauth', 'id',
               existing_type=sa.BIGINT(),
               type_=sa.INTEGER(),
               existing_nullable=False,
               autoincrement=True)
    # ### end Alembic commands ###
