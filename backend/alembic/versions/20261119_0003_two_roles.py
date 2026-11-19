"""Restrict user access to student and instructor roles.

Revision ID: 0003_two_roles
Revises: 0002_auto_approve_instructors
"""

import sqlalchemy as sa
from alembic import op

revision = "0003_two_roles"
down_revision = "0002_auto_approve_instructors"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("UPDATE users SET role = 'student' WHERE role = 'admin'")
    op.drop_constraint("ck_users_role", "users", type_="check")
    op.create_check_constraint("ck_users_role", "users", "role in ('student', 'instructor')")
    op.drop_constraint("ck_users_instructor_status", "users", type_="check")
    op.drop_column("users", "instructor_status")


def downgrade() -> None:
    op.add_column("users", sa.Column("instructor_status", sa.String(32), nullable=False, server_default="not_applicable"))
    op.create_check_constraint(
        "ck_users_instructor_status",
        "users",
        "instructor_status in ('not_applicable', 'pending', 'approved', 'rejected')",
    )
    op.drop_constraint("ck_users_role", "users", type_="check")
    op.create_check_constraint("ck_users_role", "users", "role in ('student', 'instructor', 'admin')")
    op.alter_column("users", "instructor_status", server_default=None)
