"""extend alembic version length

Revision ID: 20250115_extend_alembic_version_length
Revises: 20250101_add_user_links
Create Date: 2025-01-15 00:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = '20250115_extend_alembic_version_length'
down_revision = '20250101_add_user_links'
branch_labels = None
depends_on = None


TARGET_LENGTH = 64


def _needs_resize(bind) -> bool:
    inspector = inspect(bind)
    try:
        columns = inspector.get_columns('alembic_version')
    except Exception:  # noqa: BLE001
        return False
    for column in columns:
        if column.get('name') == 'version_num':
            length = getattr(column.get('type'), 'length', None)
            return length is not None and length < TARGET_LENGTH
    return False


def upgrade() -> None:
    bind = op.get_bind()
    if _needs_resize(bind):
        op.execute(sa.text(f"ALTER TABLE alembic_version MODIFY version_num VARCHAR({TARGET_LENGTH})"))


def downgrade() -> None:
    # no-op: shrinking the alembic_version column is unsafe once expanded
    pass
