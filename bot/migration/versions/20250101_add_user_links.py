"""add user links table

Revision ID: 20250101_add_user_links
Revises: 20240820_manual_payment_details
Create Date: 2025-01-01 00:00:00
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20250101_add_user_links'
down_revision = '20240820_manual_payment_details'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'user_links',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('tg_id', sa.BigInteger(), nullable=False),
        sa.Column('tg_username', sa.String(length=64), nullable=True),
        sa.Column('marzban_user', sa.String(length=64), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('id'),
    )
    op.create_index('ix_user_links_tg_id', 'user_links', ['tg_id'], unique=False)
    op.create_index(
        'ux_user_links_marzban_user', 'user_links', ['marzban_user'], unique=True
    )


def downgrade() -> None:
    op.drop_index('ux_user_links_marzban_user', table_name='user_links')
    op.drop_index('ix_user_links_tg_id', table_name='user_links')
    op.drop_table('user_links')
