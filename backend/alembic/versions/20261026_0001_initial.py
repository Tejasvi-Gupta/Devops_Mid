"""Initial schema."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("password_hash", sa.String(512)),
        sa.Column("google_sub", sa.String(255)),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("account_status", sa.String(32), nullable=False),
        sa.Column("instructor_status", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("google_sub"),
        sa.CheckConstraint("role in ('student', 'instructor', 'admin')", name="ck_users_role"),
        sa.CheckConstraint("account_status in ('active', 'suspended')", name="ck_users_account_status"),
        sa.CheckConstraint(
            "instructor_status in ('not_applicable', 'pending', 'approved', 'rejected')",
            name="ck_users_instructor_status",
        ),
        sa.CheckConstraint("email = lower(email)", name="ck_users_email_lower"),
    )
    op.create_table(
        "refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("csrf_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("replaced_by_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])
    op.create_table(
        "courses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("class_code", sa.String(64), nullable=False),
        sa.Column("instructor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status in ('active', 'archived')", name="ck_courses_status"),
    )
    op.create_index("ix_courses_instructor_id", "courses", ["instructor_id"])
    op.create_table(
        "enrollments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("student_id", "course_id", name="uq_enrollment_student_course"),
        sa.CheckConstraint("status in ('active', 'removed')", name="ck_enrollments_status"),
    )
    op.create_table(
        "environments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("current_published_revision_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "environment_revisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("environment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("environments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("specification", postgresql.JSONB(), nullable=False),
        sa.Column("publication_status", sa.String(32), nullable=False),
        sa.Column("published_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("environment_id", "revision_number", name="uq_revision_number"),
        sa.CheckConstraint("publication_status in ('draft', 'published')", name="ck_revision_status"),
    )
    op.create_foreign_key(
        "fk_env_current_revision",
        "environments",
        "environment_revisions",
        ["current_published_revision_id"],
        ["id"],
    )
    op.create_table(
        "software_requirements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("revision_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("environment_revisions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tool", sa.String(64), nullable=False),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("version_constraint", sa.String(120), nullable=False),
        sa.Column("mandatory", sa.Boolean(), nullable=False),
        sa.Column("install_strategy", sa.String(32), nullable=False),
        sa.Column("config", postgresql.JSONB(), nullable=False),
        sa.Column("verification", postgresql.JSONB(), nullable=False),
        sa.CheckConstraint("install_strategy in ('winget', 'verify_only')", name="ck_requirement_strategy"),
    )
    op.create_index("ix_software_requirements_revision_id", "software_requirements", ["revision_id"])
    op.create_table(
        "agent_devices",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("platform", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("credential_hash", sa.String(64), nullable=False),
        sa.Column("registered_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True)),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("credential_hash"),
        sa.CheckConstraint("status in ('active', 'revoked')", name="ck_devices_status"),
    )
    op.create_index("ix_agent_devices_student_id", "agent_devices", ["student_id"])
    op.create_index(
        "uq_one_active_device_per_student",
        "agent_devices",
        ["student_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )
    op.create_table(
        "pairing_codes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True)),
        sa.Column("replace_existing", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("code_hash"),
    )
    op.create_index("ix_pairing_codes_user_id", "pairing_codes", ["user_id"])
    op.create_table(
        "installation_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("device_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agent_devices.id"), nullable=False),
        sa.Column("revision_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("environment_revisions.id"), nullable=False),
        sa.Column("operation", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("idempotency_key", sa.String(80), nullable=False),
        sa.Column("approval_state", sa.String(32), nullable=False),
        sa.Column("cancel_requested", sa.Boolean(), nullable=False),
        sa.Column("error_summary", sa.Text()),
        sa.Column("plan", postgresql.JSONB()),
        sa.Column("detection", postgresql.JSONB()),
        sa.Column("acknowledgements", postgresql.JSONB()),
        sa.Column("retry_of_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("installation_jobs.id")),
        sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("idempotency_key"),
        sa.CheckConstraint(
            "status in ('pending','planning','awaiting_approval','installing','verifying','completed','failed','cancelled','needs_attention')",
            name="ck_jobs_status",
        ),
        sa.CheckConstraint("operation in ('provision', 'verify')", name="ck_jobs_operation"),
        sa.CheckConstraint("approval_state in ('not_required', 'pending', 'approved')", name="ck_jobs_approval"),
    )
    op.create_index(
        "uq_one_active_job",
        "installation_jobs",
        ["student_id", "device_id", "revision_id", "operation"],
        unique=True,
        postgresql_where=sa.text("status in ('pending','planning','awaiting_approval','installing','verifying')"),
    )
    op.create_table(
        "job_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("installation_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("progress", sa.Integer()),
        sa.Column("tool", sa.String(64)),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("details", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_job_events_job_id", "job_events", ["job_id"])
    op.create_table(
        "verification_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("installation_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tool", sa.String(64), nullable=False),
        sa.Column("required_constraint", sa.String(120), nullable=False),
        sa.Column("detected_version", sa.String(64)),
        sa.Column("outcome", sa.String(32), nullable=False),
        sa.Column("mandatory", sa.Boolean(), nullable=False),
        sa.Column("details", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_verification_results_job_id", "verification_results", ["job_id"])
    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("recipient_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", sa.String(64), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_notifications_recipient_id", "notifications", ["recipient_id"])
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("action", sa.String(80), nullable=False),
        sa.Column("target_type", sa.String(80), nullable=False),
        sa.Column("target_id", sa.String(80), nullable=False),
        sa.Column("outcome", sa.String(32), nullable=False),
        sa.Column("context", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_audit_logs_actor_id", "audit_logs", ["actor_id"])
    op.create_table(
        "compliance_states",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("environment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("environments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("revision_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("environment_revisions.id")),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("installation_jobs.id")),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("summary", postgresql.JSONB(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("student_id", "environment_id", name="uq_compliance_student_environment"),
        sa.CheckConstraint(
            "status in ('not_checked','ready','not_ready','needs_update','in_progress','failed','needs_attention')",
            name="ck_compliance_status",
        ),
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION epp_reject_published_revision_update()
        RETURNS trigger AS $$
        BEGIN
          IF OLD.publication_status = 'published' THEN
            RAISE EXCEPTION 'published revisions are immutable';
          END IF;
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER trg_revision_immutable
        BEFORE UPDATE ON environment_revisions
        FOR EACH ROW EXECUTE FUNCTION epp_reject_published_revision_update();

        CREATE OR REPLACE FUNCTION epp_reject_requirement_change_when_published()
        RETURNS trigger AS $$
        DECLARE
          rev_status text;
          rev_id uuid;
        BEGIN
          IF TG_OP = 'DELETE' THEN
            rev_id := OLD.revision_id;
          ELSE
            rev_id := NEW.revision_id;
          END IF;
          SELECT publication_status INTO rev_status FROM environment_revisions WHERE id = rev_id;
          IF rev_status = 'published' THEN
            RAISE EXCEPTION 'published revisions are immutable';
          END IF;
          IF TG_OP = 'DELETE' THEN
            RETURN OLD;
          END IF;
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER trg_requirements_immutable
        BEFORE INSERT OR UPDATE OR DELETE ON software_requirements
        FOR EACH ROW EXECUTE FUNCTION epp_reject_requirement_change_when_published();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_requirements_immutable ON software_requirements")
    op.execute("DROP TRIGGER IF EXISTS trg_revision_immutable ON environment_revisions")
    op.execute("DROP FUNCTION IF EXISTS epp_reject_requirement_change_when_published")
    op.execute("DROP FUNCTION IF EXISTS epp_reject_published_revision_update")
    for name in (
        "compliance_states",
        "audit_logs",
        "notifications",
        "verification_results",
        "job_events",
        "installation_jobs",
        "pairing_codes",
        "agent_devices",
        "software_requirements",
        "environment_revisions",
        "environments",
        "enrollments",
        "courses",
        "refresh_tokens",
        "users",
    ):
        op.drop_table(name)
