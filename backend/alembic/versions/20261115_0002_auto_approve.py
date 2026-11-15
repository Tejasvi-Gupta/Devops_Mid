"""Auto approve existing instructors.

Revision ID: 0002_auto_approve_instructors
Revises: 0001_initial
Create Date: 2026-11-15 22:49:00.000000

"""

from alembic import op

revision = "0002_auto_approve_instructors"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Auto-approve any instructors in the database who are currently pending
    op.execute(
        "UPDATE users SET instructor_status = 'approved' WHERE role = 'instructor' AND instructor_status = 'pending'"
    )


def downgrade() -> None:
    pass

