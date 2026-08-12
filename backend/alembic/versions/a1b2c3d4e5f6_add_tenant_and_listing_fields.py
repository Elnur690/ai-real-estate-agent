"""Add missing tenant and listing fields

Revision ID: a1b2c3d4e5f6
Revises: ee11e43bbb78
Create Date: 2026-08-12 08:05:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'ee11e43bbb78'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Add columns to tenants table if missing
    op.execute("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS backup_enabled BOOLEAN DEFAULT FALSE")
    op.execute("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS backup_frequency_days INTEGER DEFAULT 7")
    op.execute("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS last_backup_at TIMESTAMP WITH TIME ZONE NULL")
    op.execute("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS feature_makler_detector BOOLEAN DEFAULT FALSE")
    op.execute("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS feature_avm_bargain_finder BOOLEAN DEFAULT FALSE")
    op.execute("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS feature_b2b_cobrokering BOOLEAN DEFAULT FALSE")
    op.execute("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS feature_social_brochure BOOLEAN DEFAULT FALSE")
    op.execute("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS feature_client_intake_bot BOOLEAN DEFAULT FALSE")
    op.execute("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS referral_code VARCHAR(50) NULL")
    op.execute("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS referred_by_tenant_id INTEGER NULL")
    op.execute("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS referral_balance FLOAT DEFAULT 0.0")

    # Add columns to listings table if missing
    op.execute("ALTER TABLE listings ADD COLUMN IF NOT EXISTS is_first_posting BOOLEAN DEFAULT TRUE")
    op.execute("ALTER TABLE listings ADD COLUMN IF NOT EXISTS earlier_posting_url VARCHAR(1000) NULL")
    op.execute("ALTER TABLE listings ADD COLUMN IF NOT EXISTS makler_score FLOAT DEFAULT 0.0")
    op.execute("ALTER TABLE listings ADD COLUMN IF NOT EXISTS price_per_sqm FLOAT NULL")
    op.execute("ALTER TABLE listings ADD COLUMN IF NOT EXISTS district_avg_sqm FLOAT NULL")
    op.execute("ALTER TABLE listings ADD COLUMN IF NOT EXISTS bargain_percentage FLOAT NULL")

def downgrade() -> None:
    pass
