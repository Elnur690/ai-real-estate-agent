"""Add addon_aged_tiers, addon_aged_max_months, addon_saved_searches, and addon_search_tiers to plans

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-08-22 13:52:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'f6a7b8c9d0e1'
down_revision: Union[str, None] = 'e5f6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.execute("""
    ALTER TABLE plans ADD COLUMN IF NOT EXISTS addon_aged_max_months INTEGER DEFAULT 12;
    ALTER TABLE plans ADD COLUMN IF NOT EXISTS addon_aged_tiers JSON DEFAULT '[]'::json;
    ALTER TABLE plans ADD COLUMN IF NOT EXISTS addon_saved_searches INTEGER DEFAULT 0;
    ALTER TABLE plans ADD COLUMN IF NOT EXISTS addon_search_tiers JSON DEFAULT '[]'::json;
    """)

def downgrade() -> None:
    op.execute("""
    ALTER TABLE plans DROP COLUMN IF EXISTS addon_aged_max_months;
    ALTER TABLE plans DROP COLUMN IF EXISTS addon_aged_tiers;
    ALTER TABLE plans DROP COLUMN IF EXISTS addon_saved_searches;
    ALTER TABLE plans DROP COLUMN IF EXISTS addon_search_tiers;
    """)
