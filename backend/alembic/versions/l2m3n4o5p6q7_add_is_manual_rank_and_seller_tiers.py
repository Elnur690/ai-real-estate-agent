"""Add is_manual_rank and ensure seller tier columns exist

Revision ID: l2m3n4o5p6q7
Revises: k1l2m3n4o5p6
Create Date: 2026-09-21 10:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'l2m3n4o5p6q7'
down_revision: Union[str, None] = 'k1l2m3n4o5p6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.execute("""
    ALTER TABLE sellers ADD COLUMN IF NOT EXISTS rank VARCHAR(50) DEFAULT 'Bronze';
    ALTER TABLE sellers ADD COLUMN IF NOT EXISTS is_manual_rank BOOLEAN DEFAULT FALSE;
    ALTER TABLE sellers ADD COLUMN IF NOT EXISTS free_trial_feature_watermark_images BOOLEAN DEFAULT FALSE;
    ALTER TABLE sellers ADD COLUMN IF NOT EXISTS free_trial_image_requests INTEGER DEFAULT 5;
    ALTER TABLE seller_packages ADD COLUMN IF NOT EXISTS feature_watermark_free_images BOOLEAN DEFAULT FALSE;
    ALTER TABLE seller_packages ADD COLUMN IF NOT EXISTS included_image_requests INTEGER DEFAULT 0;
    ALTER TABLE seller_packages ADD COLUMN IF NOT EXISTS addon_image_requests_price FLOAT DEFAULT 10.0;
    ALTER TABLE seller_packages ADD COLUMN IF NOT EXISTS addon_image_tiers JSON DEFAULT '[]'::json;
    ALTER TABLE plans ADD COLUMN IF NOT EXISTS addon_image_tiers JSON DEFAULT '[]'::json;
    """)

def downgrade() -> None:
    op.execute("""
    ALTER TABLE sellers DROP COLUMN IF EXISTS is_manual_rank;
    ALTER TABLE seller_packages DROP COLUMN IF EXISTS addon_image_tiers;
    """)
