"""Add agent custom domain fields and reseller domain support

Revision ID: j0k1l2m3n4o5
Revises: i9j0k1l2m3n4
Create Date: 2026-09-04 10:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'j0k1l2m3n4o5'
down_revision: Union[str, None] = 'i9j0k1l2m3n4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.execute("""
    ALTER TABLE tenants ADD COLUMN IF NOT EXISTS feature_custom_domain BOOLEAN DEFAULT FALSE;
    ALTER TABLE tenants ADD COLUMN IF NOT EXISTS custom_domain VARCHAR(255);
    CREATE UNIQUE INDEX IF NOT EXISTS ix_tenants_custom_domain ON tenants(custom_domain);
    ALTER TABLE tenants ADD COLUMN IF NOT EXISTS custom_domain_enabled BOOLEAN DEFAULT FALSE;
    ALTER TABLE tenants ADD COLUMN IF NOT EXISTS custom_domain_status VARCHAR(50) DEFAULT 'disabled';
    ALTER TABLE tenants ADD COLUMN IF NOT EXISTS addon_custom_domain_price FLOAT DEFAULT 5.0;
    ALTER TABLE tenants ADD COLUMN IF NOT EXISTS custom_domain_expires_at TIMESTAMP WITH TIME ZONE;

    ALTER TABLE plans ADD COLUMN IF NOT EXISTS feature_custom_domain BOOLEAN DEFAULT FALSE;
    ALTER TABLE plans ADD COLUMN IF NOT EXISTS addon_custom_domain_price FLOAT DEFAULT 5.0;

    ALTER TABLE seller_packages ADD COLUMN IF NOT EXISTS feature_custom_domain BOOLEAN DEFAULT FALSE;
    ALTER TABLE seller_packages ADD COLUMN IF NOT EXISTS addon_custom_domain_price FLOAT DEFAULT 5.0;

    ALTER TABLE sellers ADD COLUMN IF NOT EXISTS free_trial_feature_custom_domain BOOLEAN DEFAULT FALSE;
    """)

def downgrade() -> None:
    op.execute("""
    DROP INDEX IF EXISTS ix_tenants_custom_domain;
    ALTER TABLE tenants DROP COLUMN IF EXISTS custom_domain_expires_at;
    ALTER TABLE tenants DROP COLUMN IF EXISTS addon_custom_domain_price;
    ALTER TABLE tenants DROP COLUMN IF EXISTS custom_domain_status;
    ALTER TABLE tenants DROP COLUMN IF EXISTS custom_domain_enabled;
    ALTER TABLE tenants DROP COLUMN IF EXISTS custom_domain;
    ALTER TABLE tenants DROP COLUMN IF EXISTS feature_custom_domain;

    ALTER TABLE plans DROP COLUMN IF EXISTS addon_custom_domain_price;
    ALTER TABLE plans DROP COLUMN IF EXISTS feature_custom_domain;

    ALTER TABLE seller_packages DROP COLUMN IF EXISTS addon_custom_domain_price;
    ALTER TABLE seller_packages DROP COLUMN IF EXISTS feature_custom_domain;

    ALTER TABLE sellers DROP COLUMN IF EXISTS free_trial_feature_custom_domain;
    """)
