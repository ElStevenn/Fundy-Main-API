"""Added SubscriptionPlan and Bot models

Revision ID: 12cecaf527c8
Revises: 540222424dd2
Create Date: 2025-01-18 16:49:48.727307

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '12cecaf527c8'
down_revision: Union[str, None] = '540222424dd2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('bot_definitions')
    op.alter_column('bots', 'strategy',
               existing_type=sa.VARCHAR(length=100),
               nullable=False)
    op.drop_constraint('bots_bot_definition_id_fkey', 'bots', type_='foreignkey')
    op.drop_column('bots', 'bot_definition_id')
    op.drop_column('user_configuration', 'webpage_url')
    op.drop_column('user_configuration', 'location')
    op.drop_column('user_configuration', 'main_used_exchange')
    op.drop_column('user_configuration', 'trading_experience')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('user_configuration', sa.Column('trading_experience', sa.VARCHAR(length=20), autoincrement=False, nullable=True))
    op.add_column('user_configuration', sa.Column('main_used_exchange', sa.TEXT(), autoincrement=False, nullable=True))
    op.add_column('user_configuration', sa.Column('location', sa.TEXT(), autoincrement=False, nullable=True))
    op.add_column('user_configuration', sa.Column('webpage_url', sa.TEXT(), autoincrement=False, nullable=True))
    op.add_column('bots', sa.Column('bot_definition_id', sa.UUID(), autoincrement=False, nullable=False))
    op.create_foreign_key('bots_bot_definition_id_fkey', 'bots', 'bot_definitions', ['bot_definition_id'], ['id'])
    op.alter_column('bots', 'strategy',
               existing_type=sa.VARCHAR(length=100),
               nullable=True)
    op.create_table('bot_definitions',
    sa.Column('id', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('name', sa.VARCHAR(length=255), autoincrement=False, nullable=False),
    sa.Column('description', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('logic_parameters', postgresql.JSON(astext_type=sa.Text()), autoincrement=False, nullable=True),
    sa.Column('status', sa.VARCHAR(length=50), autoincrement=False, nullable=True),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=True),
    sa.PrimaryKeyConstraint('id', name='bot_definitions_pkey'),
    sa.UniqueConstraint('name', name='bot_definitions_name_key')
    )
    # ### end Alembic commands ###
