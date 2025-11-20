"""add manual payment links table

Revision ID: 20250220_add_manual_payment_links
Revises: 20250101_add_user_links
Create Date: 2025-02-20 00:00:00
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20250220_add_manual_payment_links'
down_revision = '20250101_add_user_links'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'manual_payment_links',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('payment_id', sa.BigInteger(), nullable=False),
        sa.Column('marzban_user', sa.String(length=64), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('id'),
    )
    op.create_index('ix_manual_payment_links_payment_id', 'manual_payment_links', ['payment_id'], unique=False)
    op.create_index('ix_manual_payment_links_marzban_user', 'manual_payment_links', ['marzban_user'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_manual_payment_links_marzban_user', table_name='manual_payment_links')
    op.drop_index('ix_manual_payment_links_payment_id', table_name='manual_payment_links')
    op.drop_table('manual_payment_links')
