"""Add preferred_billing_day and independent addon expiration fields to tenants

Revision ID: h8i9j0k1l2m3
Revises: g7h8i9j0k1l2
Create Date: 2026-08-28 10:25:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'h8i9j0k1l2m3'
down_revision: Union[str, None] = 'g7h8i9j0k1l2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.execute("""
    -- Tenants table
    ALTER TABLE tenants ADD COLUMN IF NOT EXISTS preferred_billing_day INTEGER DEFAULT 1;
    ALTER TABLE tenants ADD COLUMN IF NOT EXISTS crm_expires_at TIMESTAMP WITH TIME ZONE;
    ALTER TABLE tenants ADD COLUMN IF NOT EXISTS aged_expires_at TIMESTAMP WITH TIME ZONE;
    """)

def downgrade() -> None:
    op.execute("""
    ALTER TABLE tenants DROP COLUMN IF EXISTS preferred_billing_day;
    ALTER TABLE tenants DROP COLUMN IF EXISTS crm_expires_at;
    ALTER TABLE tenants DROP COLUMN IF EXISTS aged_expires_at;
    """)
