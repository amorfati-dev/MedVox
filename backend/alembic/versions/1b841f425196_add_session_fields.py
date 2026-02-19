"""add_session_fields

Revision ID: 1b841f425196
Revises: e39a50febfe6
Create Date: 2026-02-12 14:41:01.376289

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1b841f425196'
down_revision: Union[str, None] = 'e39a50febfe6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add processing_mode column
    op.add_column('recordings', sa.Column('processing_mode', sa.String(20), nullable=False, server_default='with_billing'))

    # Add session_metadata JSON column
    op.add_column('recordings', sa.Column('session_metadata', sa.JSON, nullable=True))

    # Create index for efficient session queries
    op.create_index('idx_recordings_session_query', 'recordings', ['created_at', 'status', 'created_by_id'])


def downgrade() -> None:
    # Drop index
    op.drop_index('idx_recordings_session_query', table_name='recordings')

    # Drop columns
    op.drop_column('recordings', 'session_metadata')
    op.drop_column('recordings', 'processing_mode')
