"""Alembic migrations initialization"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# User table
op.create_table(
    'user',
    sa.Column('id', sa.String(36), nullable=False),
    sa.Column('email', sa.String(255), nullable=False),
    sa.Column('hashed_password', sa.String(255), nullable=False),
    sa.Column('api_key', sa.String(255), nullable=False),
    sa.Column('role', sa.String(20), nullable=False),
    sa.Column('created_at', sa.DateTime, default=sa.func.now()),
    sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now()),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email'),
    sa.UniqueConstraint('api_key'),
)

op.create_index('ix_user_email', 'user', ['email'])
op.create_index('ix_user_api_key', 'user', ['api_key'])

# UserCredits table
op.create_table(
    'user_credits',
    sa.Column('id', sa.String(36), nullable=False),
    sa.Column('user_id', sa.String(36), nullable=False),
    sa.Column('virtual_credits', sa.Float, nullable=False, default=0),
    sa.Column('last_daily_bonus', sa.DateTime),
    sa.Column('created_at', sa.DateTime, default=sa.func.now()),
    sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now()),
    sa.PrimaryKeyConstraint('id'),
    sa.ForeignKeyConstraint(['user_id'], ['user.id']),
)

op.create_index('ix_user_credits_user_id', 'user_credits', ['user_id'], unique=True)

# CreditLedger table
op.create_table(
    'credit_ledger',
    sa.Column('id', sa.String(36), nullable=False),
    sa.Column('user_id', sa.String(36), nullable=False),
    sa.Column('amount', sa.Float, nullable=False),
    sa.Column('balance_after', sa.Float, nullable=False),
    sa.Column('transaction_type', sa.String(50), nullable=False),
    sa.Column('created_at', sa.DateTime, default=sa.func.now()),
    sa.PrimaryKeyConstraint('id'),
    sa.ForeignKeyConstraint(['user_id'], ['user.id']),
)

op.create_index('ix_credit_ledger_user_id', 'credit_ledger', ['user_id'])
op.create_index('ix_credit_ledger_created_at', 'credit_ledger', ['created_at'])
op.create_index('ix_credit_ledger_type', 'credit_ledger', ['transaction_type'])

# Provider table
op.create_table(
    'provider',
    sa.Column('id', sa.String(36), nullable=False),
    sa.Column('user_id', sa.String(36), nullable=False),
    sa.Column('status', sa.String(20), default='inactive'),
    sa.Column('ram_allocated_gb', sa.Float, default=0),
    sa.Column('cpu_cores_allocated', sa.Integer, default=0),
    sa.Column('reputation_score', sa.Float, default=0),
    sa.Column('total_tasks_completed', sa.Integer, default=0),
    sa.Column('last_heartbeat', sa.DateTime),
    sa.Column('created_at', sa.DateTime, default=sa.func.now()),
    sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now()),
    sa.PrimaryKeyConstraint('id'),
    sa.ForeignKeyConstraint(['user_id'], ['user.id']),
)

op.create_index('ix_provider_user_id', 'provider', ['user_id'], unique=True)
op.create_index('ix_provider_status', 'provider', ['status'])

# ProviderResources table
op.create_table(
    'provider_resources',
    sa.Column('id', sa.String(36), nullable=False),
    sa.Column('provider_id', sa.String(36), nullable=False),
    sa.Column('ram_used_mb', sa.Float, default=0),
    sa.Column('cpu_percent', sa.Float, default=0),
    sa.Column('gpu_percent', sa.Float, default=0),
    sa.Column('timestamp', sa.DateTime, default=sa.func.now()),
    sa.Column('reported_by_provider', sa.Boolean, default=False),
    sa.PrimaryKeyConstraint('id'),
    sa.ForeignKeyConstraint(['provider_id'], ['provider.id']),
)

op.create_index('ix_provider_resources_provider_id', 'provider_resources', ['provider_id'])
op.create_index('ix_provider_resources_timestamp', 'provider_resources', ['timestamp'])

# Task table
op.create_table(
    'task',
    sa.Column('id', sa.String(36), nullable=False),
    sa.Column('consumer_id', sa.String(36), nullable=False),
    sa.Column('provider_id', sa.String(36)),
    sa.Column('status', sa.String(20), default='pending'),
    sa.Column('priority', sa.String(20), default='normal'),
    sa.Column('llm_model', sa.String(100), nullable=False),
    sa.Column('prompt', sa.Text, nullable=False),
    sa.Column('result', sa.Text),
    sa.Column('error_message', sa.String(1000)),
    sa.Column('simulated_cost_credits', sa.Float, default=0),
    sa.Column('completion_time', sa.Float),
    sa.Column('assigned_at', sa.DateTime),
    sa.Column('completed_at', sa.DateTime),
    sa.Column('created_at', sa.DateTime, default=sa.func.now()),
    sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now()),
    sa.PrimaryKeyConstraint('id'),
    sa.ForeignKeyConstraint(['consumer_id'], ['user.id']),
    sa.ForeignKeyConstraint(['provider_id'], ['provider.id']),
)

op.create_index('ix_task_status', 'task', ['status'])
op.create_index('ix_task_consumer_id', 'task', ['consumer_id'])
op.create_index('ix_task_provider_id', 'task', ['provider_id'])
op.create_index('ix_task_created_at', 'task', ['created_at'])

# AuditLog table
op.create_table(
    'audit_log',
    sa.Column('id', sa.String(36), nullable=False),
    sa.Column('timestamp', sa.DateTime, default=sa.func.now()),
    sa.Column('actor_type', sa.String(50)),
    sa.Column('actor_id', sa.String(36)),
    sa.Column('action', sa.String(100), nullable=False),
    sa.Column('resource_id', sa.String(36)),
    sa.Column('details', sa.JSON),
    sa.PrimaryKeyConstraint('id'),
)

op.create_index('ix_audit_log_actor_id', 'audit_log', ['actor_id'])
op.create_index('ix_audit_log_timestamp', 'audit_log', ['timestamp'])
op.create_index('ix_audit_log_action', 'audit_log', ['action'])
