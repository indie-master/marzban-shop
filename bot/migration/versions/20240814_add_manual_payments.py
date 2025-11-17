"""add manual payments table

Revision ID: 20240814_add_manual_payments
Revises: 36159a9e6985
Create Date: 2024-08-14 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20240814_add_manual_payments'
down_revision = '36159a9e6985'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'manual_payments',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('tg_id', sa.BigInteger(), nullable=True),
        sa.Column('username', sa.String(length=64), nullable=True),
        sa.Column('lang', sa.String(length=64), nullable=True),
        sa.Column('chat_id', sa.BigInteger(), nullable=True),
        sa.Column('callback', sa.String(length=64), nullable=True),
        sa.Column('status', sa.String(length=64), nullable=True),
        sa.Column('proof_message_id', sa.BigInteger(), nullable=True),
        sa.Column('proof_chat_id', sa.BigInteger(), nullable=True),
        sa.Column('admin_message_id', sa.BigInteger(), nullable=True),
        sa.Column('admin_chat_id', sa.BigInteger(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('manual_payments')
