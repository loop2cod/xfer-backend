"""add_admin_remarks_and_status_history

Revision ID: eec58f467c19
Revises: 4c00de9372eb
Create Date: 2025-07-01 16:58:41.938425

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'eec58f467c19'
down_revision = '4c00de9372eb'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add admin_remarks column
    op.add_column('transfer_requests', sa.Column('admin_remarks', sa.Text(), nullable=True))

    # Add internal_notes column
    op.add_column('transfer_requests', sa.Column('internal_notes', sa.Text(), nullable=True))

    # Add status_history column
    op.add_column('transfer_requests', sa.Column('status_history', sa.JSON(), nullable=True))


def downgrade() -> None:
    # Remove the added columns
    op.drop_column('transfer_requests', 'status_history')
    op.drop_column('transfer_requests', 'internal_notes')
    op.drop_column('transfer_requests', 'admin_remarks')