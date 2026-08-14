"""Add multi_location fields to plans and tenants

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-08-14 16:25:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.execute("""
    ALTER TABLE plans ADD COLUMN IF NOT EXISTS feature_multi_location BOOLEAN DEFAULT TRUE;
    ALTER TABLE plans ADD COLUMN IF NOT EXISTS max_locations_per_search INTEGER DEFAULT 5;
    ALTER TABLE tenants ADD COLUMN IF NOT EXISTS feature_multi_location BOOLEAN DEFAULT TRUE;
    ALTER TABLE tenants ADD COLUMN IF NOT EXISTS max_locations_per_search INTEGER DEFAULT 5;
    """)

def downgrade() -> None:
    op.execute("""
    ALTER TABLE plans DROP COLUMN IF EXISTS feature_multi_location;
    ALTER TABLE plans DROP COLUMN IF EXISTS max_locations_per_search;
    ALTER TABLE tenants DROP COLUMN IF EXISTS feature_multi_location;
    ALTER TABLE tenants DROP COLUMN IF EXISTS max_locations_per_search;
    """)
