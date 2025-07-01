"""add transfer_id column to transfer_requests

Revision ID: 001
Revises: 
Create Date: 2025-06-30 12:50:00.000000

"""
from alembic import op
import sqlalchemy as sa
import random
import string

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def generate_transfer_id() -> str:
    """Generate alphanumeric transfer ID in format TX-XXXXXXXX"""
    random_digits = ''.join(random.choices(string.digits, k=8))
    return f"TX-{random_digits}"


def upgrade() -> None:
    # Add the transfer_id column as nullable first
    op.add_column('transfer_requests', sa.Column('transfer_id', sa.String(20), nullable=True))

    # Populate existing records with transfer IDs
    connection = op.get_bind()
    result = connection.execute(sa.text("SELECT id FROM transfer_requests"))
    for row in result:
        transfer_id = generate_transfer_id()
        # Ensure uniqueness by checking if it already exists
        while True:
            existing = connection.execute(
                sa.text("SELECT id FROM transfer_requests WHERE transfer_id = :transfer_id"),
                {"transfer_id": transfer_id}
            ).fetchone()
            if not existing:
                break
            transfer_id = generate_transfer_id()

        connection.execute(
            sa.text("UPDATE transfer_requests SET transfer_id = :transfer_id WHERE id = :id"),
            {"transfer_id": transfer_id, "id": row[0]}
        )

    # Create unique index on transfer_id
    op.create_index('ix_transfer_requests_transfer_id', 'transfer_requests', ['transfer_id'], unique=True)


def downgrade() -> None:
    # Remove the index and column
    op.drop_index('ix_transfer_requests_transfer_id', table_name='transfer_requests')
    op.drop_column('transfer_requests', 'transfer_id')
