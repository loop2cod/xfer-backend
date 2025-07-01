"""add customer_id to users

Revision ID: 002
Revises: eec58f467c19
Create Date: 2025-07-01 16:50:00.000000

"""
from alembic import op
import sqlalchemy as sa
import random
import string

# revision identifiers, used by Alembic.
revision = '002'
down_revision = 'eec58f467c19'
branch_labels = None
depends_on = None


def generate_customer_id() -> str:
    """Generate alphanumeric customer ID in format CT-XXXXXXXX"""
    random_digits = ''.join(random.choices(string.digits, k=8))
    return f"CT-{random_digits}"


def upgrade() -> None:
    # Add the customer_id column as nullable first
    op.add_column('users', sa.Column('customer_id', sa.String(20), nullable=True))

    # Populate existing records with customer IDs
    connection = op.get_bind()
    result = connection.execute(sa.text("SELECT id FROM users"))
    for row in result:
        customer_id = generate_customer_id()
        # Ensure uniqueness by checking if it already exists
        while True:
            existing = connection.execute(
                sa.text("SELECT id FROM users WHERE customer_id = :customer_id"),
                {"customer_id": customer_id}
            ).fetchone()
            if not existing:
                break
            customer_id = generate_customer_id()

        connection.execute(
            sa.text("UPDATE users SET customer_id = :customer_id WHERE id = :id"),
            {"customer_id": customer_id, "id": row[0]}
        )

    # Now make the column non-nullable and add unique constraint
    op.alter_column('users', 'customer_id', nullable=False)
    op.create_unique_constraint('uq_users_customer_id', 'users', ['customer_id'])


def downgrade() -> None:
    # Remove the unique constraint and column
    op.drop_constraint('uq_users_customer_id', 'users', type_='unique')
    op.drop_column('users', 'customer_id')