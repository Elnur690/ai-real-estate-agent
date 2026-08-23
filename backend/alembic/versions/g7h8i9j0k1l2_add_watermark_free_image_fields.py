"""Add watermark_free_image fields and quotas to tenants, plans, sellers, and seller_packages

Revision ID: g7h8i9j0k1l2
Revises: f6a7b8c9d0e1
Create Date: 2026-08-23 20:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'g7h8i9j0k1l2'
down_revision: Union[str, None] = 'f6a7b8c9d0e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.execute("""
    -- Tenants table
    ALTER TABLE tenants ADD COLUMN IF NOT EXISTS feature_watermark_free_images BOOLEAN DEFAULT FALSE;
    ALTER TABLE tenants ADD COLUMN IF NOT EXISTS addon_image_requests_limit INTEGER DEFAULT 0;
    ALTER TABLE tenants ADD COLUMN IF NOT EXISTS addon_image_requests_used INTEGER DEFAULT 0;
    ALTER TABLE tenants ADD COLUMN IF NOT EXISTS addon_image_requests_price DOUBLE PRECISION DEFAULT 0.0;

    -- Plans table
    ALTER TABLE plans ADD COLUMN IF NOT EXISTS feature_watermark_free_images BOOLEAN DEFAULT FALSE;
    ALTER TABLE plans ADD COLUMN IF NOT EXISTS included_image_requests INTEGER DEFAULT 0;
    ALTER TABLE plans ADD COLUMN IF NOT EXISTS addon_image_requests_price DOUBLE PRECISION DEFAULT 10.0;
    ALTER TABLE plans ADD COLUMN IF NOT EXISTS addon_image_tiers JSON DEFAULT '[]'::json;

    -- Sellers table
    ALTER TABLE sellers ADD COLUMN IF NOT EXISTS free_trial_feature_watermark_images BOOLEAN DEFAULT FALSE;
    ALTER TABLE sellers ADD COLUMN IF NOT EXISTS free_trial_image_requests INTEGER DEFAULT 5;

    -- Seller Packages table
    ALTER TABLE seller_packages ADD COLUMN IF NOT EXISTS feature_watermark_free_images BOOLEAN DEFAULT FALSE;
    ALTER TABLE seller_packages ADD COLUMN IF NOT EXISTS included_image_requests INTEGER DEFAULT 0;
    ALTER TABLE seller_packages ADD COLUMN IF NOT EXISTS addon_image_requests_price DOUBLE PRECISION DEFAULT 10.0;
    ALTER TABLE seller_packages ADD COLUMN IF NOT EXISTS addon_image_tiers JSON DEFAULT '[]'::json;
    """)

def downgrade() -> None:
    op.execute("""
    ALTER TABLE tenants DROP COLUMN IF EXISTS feature_watermark_free_images;
    ALTER TABLE tenants DROP COLUMN IF EXISTS addon_image_requests_limit;
    ALTER TABLE tenants DROP COLUMN IF EXISTS addon_image_requests_used;
    ALTER TABLE tenants DROP COLUMN IF EXISTS addon_image_requests_price;

    ALTER TABLE plans DROP COLUMN IF EXISTS feature_watermark_free_images;
    ALTER TABLE plans DROP COLUMN IF EXISTS included_image_requests;
    ALTER TABLE plans DROP COLUMN IF EXISTS addon_image_requests_price;
    ALTER TABLE plans DROP COLUMN IF EXISTS addon_image_tiers;

    ALTER TABLE sellers DROP COLUMN IF EXISTS free_trial_feature_watermark_images;
    ALTER TABLE sellers DROP COLUMN IF EXISTS free_trial_image_requests;

    ALTER TABLE seller_packages DROP COLUMN IF EXISTS feature_watermark_free_images;
    ALTER TABLE seller_packages DROP COLUMN IF EXISTS included_image_requests;
    ALTER TABLE seller_packages DROP COLUMN IF EXISTS addon_image_requests_price;
    ALTER TABLE seller_packages DROP COLUMN IF EXISTS addon_image_tiers;
    """)
