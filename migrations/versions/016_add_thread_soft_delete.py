"""Add soft-delete to conversation_threads.

Replaces hard DELETE CASCADE with a deleted_at timestamp.
Existing rows get NULL (not deleted). All thread queries filter
on deleted_at IS NULL via a partial index.

Revision ID: 016
Revises: 015
"""

from alembic import op

revision = "016"
down_revision = "015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE conversation_threads
        ADD COLUMN deleted_at TIMESTAMPTZ DEFAULT NULL
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_threads_not_deleted
        ON conversation_threads (workspace_id, updated_at DESC)
        WHERE deleted_at IS NULL
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_threads_not_deleted")
    op.execute("ALTER TABLE conversation_threads DROP COLUMN IF EXISTS deleted_at")
