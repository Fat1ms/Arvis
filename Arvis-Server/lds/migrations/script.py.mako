"""Alembic script file"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Apply migration"""
    # This is handled by auto-generation in 001_initial_schema.py
    pass


def downgrade():
    """Revert migration"""
    pass
