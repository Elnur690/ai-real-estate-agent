"""Create plans table

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-08-12 08:06:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.execute("""
    CREATE TABLE IF NOT EXISTS plans (
        id SERIAL PRIMARY KEY,
        code VARCHAR(50) UNIQUE NOT NULL,
        name VARCHAR(255) NOT NULL,
        description TEXT NULL,
        price FLOAT DEFAULT 0.0,
        currency VARCHAR(10) DEFAULT 'AZN',
        billing_period VARCHAR(50) DEFAULT 'monthly',
        is_active BOOLEAN DEFAULT TRUE,
        max_agents INTEGER DEFAULT 1,
        feature_makler_detector BOOLEAN DEFAULT TRUE,
        feature_avm_bargain_finder BOOLEAN DEFAULT TRUE,
        feature_b2b_cobrokering BOOLEAN DEFAULT TRUE,
        feature_social_brochure BOOLEAN DEFAULT TRUE,
        feature_client_intake_bot BOOLEAN DEFAULT TRUE,
        backup_enabled BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    CREATE INDEX IF NOT EXISTS ix_plans_code ON plans (code);
    """)

def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS plans;")
