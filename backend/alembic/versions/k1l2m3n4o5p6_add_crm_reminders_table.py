"""Add crm_reminders table

Revision ID: k1l2m3n4o5p6
Revises: j0k1l2m3n4o5
Create Date: 2026-09-04 16:15:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'k1l2m3n4o5p6'
down_revision: Union[str, None] = 'j0k1l2m3n4o5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.execute("""
    CREATE TABLE IF NOT EXISTS crm_reminders (
        id SERIAL PRIMARY KEY,
        tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
        client_id INTEGER REFERENCES crm_clients(id) ON DELETE SET NULL,
        deal_id INTEGER REFERENCES crm_deals(id) ON DELETE SET NULL,
        title VARCHAR(255) NOT NULL,
        reminder_type VARCHAR(50) DEFAULT 'viewing',
        notes TEXT,
        due_at TIMESTAMP WITH TIME ZONE NOT NULL,
        remind_before_minutes INTEGER DEFAULT 60,
        status VARCHAR(50) DEFAULT 'pending',
        notified_at TIMESTAMP WITH TIME ZONE,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_crm_reminders_tenant ON crm_reminders (tenant_id, status);
    CREATE INDEX IF NOT EXISTS idx_crm_reminders_due ON crm_reminders (due_at, status);
    """)

def downgrade() -> None:
    op.execute("""
    DROP TABLE IF EXISTS crm_reminders;
    """)
