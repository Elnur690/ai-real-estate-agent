"""Add portfolio_slug to tenants table and create unique index

Revision ID: i9j0k1l2m3n4
Revises: h8i9j0k1l2m3
Create Date: 2026-09-03 16:42:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'i9j0k1l2m3n4'
down_revision: Union[str, None] = 'h8i9j0k1l2m3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.execute("""
    -- Add portfolio_slug column if not exists
    ALTER TABLE tenants ADD COLUMN IF NOT EXISTS portfolio_slug VARCHAR(100);
    
    -- Auto-populate portfolio_slug for existing tenants
    UPDATE tenants 
    SET portfolio_slug = 'agent-' || id 
    WHERE portfolio_slug IS NULL OR TRIM(portfolio_slug) = '';

    -- Create unique index
    CREATE UNIQUE INDEX IF NOT EXISTS ix_tenants_portfolio_slug ON tenants(portfolio_slug);
    """)

def downgrade() -> None:
    op.execute("""
    DROP INDEX IF EXISTS ix_tenants_portfolio_slug;
    ALTER TABLE tenants DROP COLUMN IF EXISTS portfolio_slug;
    """)
