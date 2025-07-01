"""merge_multiple_heads

Revision ID: 4c00de9372eb
Revises: 865700eeb511, a66c5842fa6b, f1234567890a
Create Date: 2025-07-01 16:58:34.407101

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4c00de9372eb'
down_revision = ('865700eeb511', 'a66c5842fa6b', 'f1234567890a')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass