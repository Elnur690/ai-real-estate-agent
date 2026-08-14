"""Add aged listings and profile fields to tenants, plans, and users

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-08-14 11:45:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Add columns to tenants table
    op.execute("""
    ALTER TABLE tenants ADD COLUMN IF NOT EXISTS feature_aged_listings BOOLEAN DEFAULT FALSE;
    ALTER TABLE tenants ADD COLUMN IF NOT EXISTS addon_aged_max_months INTEGER DEFAULT 12;
    """)

    # Add columns to plans table
    op.execute("""
    ALTER TABLE plans ADD COLUMN IF NOT EXISTS feature_aged_listings BOOLEAN DEFAULT FALSE;
    ALTER TABLE plans ADD COLUMN IF NOT EXISTS addon_aged_listings_price FLOAT DEFAULT 0.0;
    ALTER TABLE plans ADD COLUMN IF NOT EXISTS trial_days INTEGER DEFAULT 7;
    """)

    # Add columns to users table
    op.execute("""
    ALTER TABLE users ADD COLUMN IF NOT EXISTS phone VARCHAR(50) NULL;
    """)

def downgrade() -> None:
    op.execute("""
    ALTER TABLE tenants DROP COLUMN IF EXISTS feature_aged_listings;
    ALTER TABLE tenants DROP COLUMN IF EXISTS addon_aged_max_months;
    ALTER TABLE plans DROP COLUMN IF EXISTS feature_aged_listings;
    ALTER TABLE plans DROP COLUMN IF EXISTS addon_aged_listings_price;
    ALTER TABLE plans DROP COLUMN IF EXISTS trial_days;
    ALTER TABLE users DROP COLUMN IF EXISTS phone;
    """)
