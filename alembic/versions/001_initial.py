"""init

Revision ID: 001_initial
Revises:
Create Date: 2025-12-24 18:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create services table
    op.create_table(
        'services',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('endpoint', sa.String(512), nullable=False),
        sa.Column('pricing_model', sa.String(50)),  # pay-per-call, subscription, metered
        sa.Column('price_amount', sa.Numeric(20, 8), nullable=False),
        sa.Column('price_token', sa.String(42), nullable=False),
        sa.Column('mcp_compatible', sa.Boolean, default=False),
        sa.Column('reputation_score', sa.Numeric(3, 2), default=0),
        sa.Column('total_calls', sa.BigInteger, default=0),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Create payments table
    op.create_table(
        'payments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('agent_wallet', sa.String(42), nullable=False),
        sa.Column('service_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('services.id')),
        sa.Column('recipient', sa.String(42), nullable=False),
        sa.Column('amount', sa.Numeric(20, 8), nullable=False),
        sa.Column('token', sa.String(42), nullable=False),
        sa.Column('tx_hash', sa.String(66)),
        sa.Column('status', sa.String(20)),  # pending, confirmed, failed
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
    )

    # Create agent_sessions table
    op.create_table(
        'agent_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('wallet_address', sa.String(42)),
        sa.Column('config', sa.JSON),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        sa.Column('last_active', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Create execution_logs table
    op.create_table(
        'execution_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('agent_sessions.id')),
        sa.Column('command', sa.String, nullable=False),
        sa.Column('plan', sa.JSON),
        sa.Column('tool_calls', sa.JSON),
        sa.Column('result', sa.JSON),
        sa.Column('total_cost', sa.Float),
        sa.Column('duration_ms', sa.Integer),
        sa.Column('status', sa.String(20), default='running'),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
    )

    # Create approval_requests table
    op.create_table(
        'approval_requests',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('agent_sessions.id')),
        sa.Column('tool_name', sa.String(100), nullable=False),
        sa.Column('tool_args', sa.JSON, nullable=False),
        sa.Column('decision', sa.String(20)),  # pending, approved, rejected, edited
        sa.Column('edited_args', sa.JSON),
        sa.Column('decision_made_at', sa.DateTime),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
    )

    # Create service_subscriptions table
    op.create_table(
        'service_subscriptions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('agent_sessions.id')),
        sa.Column('service_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('services.id')),
        sa.Column('status', sa.String(20), default='active'),  # active, cancelled, expired
        sa.Column('expires_at', sa.DateTime),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
    )

    # Create indexes
    op.create_index('idx_payments_wallet', 'payments', ['agent_wallet'])
    op.create_index('idx_payments_created', 'payments', ['created_at'])
    op.create_index('idx_services_mcp', 'services', ['mcp_compatible'])
    op.create_index('idx_execution_session', 'execution_logs', ['session_id'])
    op.create_index('idx_approval_session', 'approval_requests', ['session_id'])


def downgrade() -> None:
    # Drop tables in reverse order to handle foreign key dependencies
    op.drop_table('service_subscriptions')
    op.drop_table('approval_requests')
    op.drop_table('execution_logs')
    op.drop_table('agent_sessions')
    op.drop_table('payments')
    op.drop_table('services')