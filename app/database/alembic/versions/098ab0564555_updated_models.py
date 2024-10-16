from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '098ab0564555'
down_revision: Union[str, None] = 'afc8708a5636'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Remove the command to add the column because it already exists
    # op.add_column('user_configuration', sa.Column('min_funding_rate_threshold', sa.Float(), nullable=True))

    # Drop the old column 'minimum_founding_rate_to_show'
    op.drop_column('user_configuration', 'minimum_founding_rate_to_show')

def downgrade() -> None:
    # Recreate the dropped column during downgrade
    op.add_column('user_configuration', sa.Column('minimum_founding_rate_to_show', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True))
    
    # Remove the 'min_funding_rate_threshold' column during downgrade
    op.drop_column('user_configuration', 'min_funding_rate_threshold')
