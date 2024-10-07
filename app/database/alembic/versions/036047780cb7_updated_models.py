"""Updated models

Revision ID: 036047780cb7
Revises: 0d4375a2a0e2
Create Date: 2024-09-23 16:02:32.475175

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
import uuid

# revision identifiers, used by Alembic.
revision = '036047780cb7'
down_revision = '0d4375a2a0e2'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Step 1: Add a new temporary UUID column
    op.add_column('monthly_subscription', sa.Column('id_new', UUID(as_uuid=True), default=uuid.uuid4, nullable=False))

    # Step 2: Populate the new column with UUIDs for existing rows
    op.execute('UPDATE monthly_subscription SET id_new = gen_random_uuid()')

    # Step 3: Drop the old 'id' column
    op.drop_column('monthly_subscription', 'id')

    # Step 4: Rename the 'id_new' column to 'id'
    op.alter_column('monthly_subscription', 'id_new', new_column_name='id')

    # Repeat the same steps for user_configuration
    op.add_column('user_configuration', sa.Column('id_new', UUID(as_uuid=True), default=uuid.uuid4, nullable=False))
    op.execute('UPDATE user_configuration SET id_new = gen_random_uuid()')
    op.drop_column('user_configuration', 'id')
    op.alter_column('user_configuration', 'id_new', new_column_name='id')

def downgrade() -> None:
    # Steps to reverse the upgrade (back to integer IDs), if necessary
    op.add_column('monthly_subscription', sa.Column('id_old', sa.INTEGER, nullable=False))
    op.execute('UPDATE monthly_subscription SET id_old = nextval(\'some_sequence\')')  # or an appropriate sequence
    op.drop_column('monthly_subscription', 'id')
    op.alter_column('monthly_subscription', 'id_old', new_column_name='id')

    op.add_column('user_configuration', sa.Column('id_old', sa.INTEGER, nullable=False))
    op.execute('UPDATE user_configuration SET id_old = nextval(\'some_sequence\')')  # or an appropriate sequence
    op.drop_column('user_configuration', 'id')
    op.alter_column('user_configuration', 'id_old', new_column_name='id')
