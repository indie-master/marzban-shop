"""add plan name and amount to manual payments

Revision ID: 20240820_manual_payment_details
Revises: 20240814_add_manual_payments
Create Date: 2024-08-20 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20240820_manual_payment_details'
down_revision = '20240814_add_manual_payments'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('manual_payments', sa.Column('plan_name', sa.String(length=128), nullable=True))
    op.add_column('manual_payments', sa.Column('amount', sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column('manual_payments', 'amount')
    op.drop_column('manual_payments', 'plan_name')
