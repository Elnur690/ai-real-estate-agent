"""Add addon_aged_tiers and addon_search_tiers to seller_packages

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-08-22 12:43:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.execute("""
    ALTER TABLE seller_packages ADD COLUMN IF NOT EXISTS addon_aged_tiers JSON DEFAULT '[]'::json;
    ALTER TABLE seller_packages ADD COLUMN IF NOT EXISTS addon_search_tiers JSON DEFAULT '[]'::json;
    """)

def downgrade() -> None:
    op.execute("""
    ALTER TABLE seller_packages DROP COLUMN IF EXISTS addon_aged_tiers;
    ALTER TABLE seller_packages DROP COLUMN IF EXISTS addon_search_tiers;
    """)
