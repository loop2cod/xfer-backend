"""add_audit_logs_table

Revision ID: 005_add_audit_logs_table
Revises: 004_add_user_activities_table
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers, used by Alembic.
revision = '005_add_audit_logs_table'
down_revision = '004_add_user_activities_table'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create audit_logs table
    op.create_table('audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('admin_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('admins.id'), nullable=False),
        sa.Column('action', sa.String(length=255), nullable=False, index=True),
        sa.Column('resource_type', sa.String(length=100), nullable=False, index=True),
        sa.Column('resource_id', sa.String(length=255), nullable=True, index=True),
        sa.Column('details', postgresql.JSON, nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), index=True),
    )
    
    # Create indexes
    op.create_index('ix_audit_logs_admin_id', 'audit_logs', ['admin_id'])
    op.create_index('ix_audit_logs_created_at_desc', 'audit_logs', ['created_at'], postgresql_ops={'created_at': 'DESC'})
    op.create_index('ix_audit_logs_action_resource', 'audit_logs', ['action', 'resource_type'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_audit_logs_action_resource', table_name='audit_logs')
    op.drop_index('ix_audit_logs_created_at_desc', table_name='audit_logs')
    op.drop_index('ix_audit_logs_admin_id', table_name='audit_logs')
    
    # Drop table
    op.drop_table('audit_logs')