"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-07-02

NOTE ON TIMESCALEDB: The blueprint's Section 2 uses plain PostgreSQL (no
TimescaleDB) — TimescaleDB was requested for this migration specifically.
Implementing it correctly requires one real tradeoff worth flagging:
TimescaleDB requires the partitioning column (created_at) to be part of
any UNIQUE/PRIMARY KEY constraint on a hypertable. So adr_reports uses a
composite primary key (id, created_at) instead of id alone. This is a
genuine behavior of TimescaleDB, not a simplification — foreign keys
that reference adr_reports.id elsewhere would need adjusting accordingly
if you add them later.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\"")
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb")

    op.create_table(
        "organizations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("country_code", sa.CHAR(2), nullable=False),
        sa.Column("plan", sa.Text, nullable=False, server_default="starter"),
        sa.Column("stripe_customer_id", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id")),
        sa.Column("email", sa.Text, unique=True, nullable=False),
        sa.Column("hashed_password", sa.Text, nullable=False),
        sa.Column("role", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("role IN ('pharmacist','admin','reviewer')", name="ck_users_role"),
    )

    op.create_table(
        "regulatory_cartridges",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("authority_code", sa.Text, nullable=False),
        sa.Column("country_code", sa.CHAR(2), nullable=False),
        sa.Column("version", sa.Text, nullable=False),
        sa.Column("field_mapping", postgresql.JSONB, nullable=False),
        sa.Column("submission_endpoint", sa.Text, nullable=True),
        sa.Column("auth_config", postgresql.JSONB, nullable=True),
        sa.Column("is_active", sa.Boolean, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("authority_code", "version", name="uq_authority_version"),
    )

    # Composite PK (id, created_at) — required for TimescaleDB hypertable partitioning on created_at.
    op.create_table(
        "adr_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id")),
        sa.Column("reporter_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("patient_demographics", postgresql.JSONB, nullable=False),
        sa.Column("suspect_drugs", postgresql.JSONB, nullable=False),
        sa.Column("reaction", postgresql.JSONB, nullable=False),
        sa.Column("narrative", sa.Text, nullable=True),
        sa.Column("source_type", sa.Text, nullable=False),
        sa.Column("extraction_confidence", sa.Numeric(3, 2), nullable=True),
        sa.Column("status", sa.Text, nullable=False, server_default="draft"),
        sa.Column("target_authority", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", "created_at", name="pk_adr_reports"),
        sa.CheckConstraint("source_type IN ('text','image_ocr','voice','manual_form')", name="ck_reports_source_type"),
        sa.CheckConstraint("status IN ('draft','pending_review','in_flight','submitted','acknowledged','rejected')", name="ck_reports_status"),
    )

    op.execute(
        "SELECT create_hypertable('adr_reports', 'created_at', chunk_time_interval => INTERVAL '7 days')"
    )

    op.create_index("idx_adr_reports_org_status", "adr_reports", ["organization_id", "status"])
    op.execute("CREATE INDEX idx_adr_reports_jsonb_drugs ON adr_reports USING GIN (suspect_drugs)")
    op.execute("CREATE INDEX idx_adr_reports_jsonb_reaction ON adr_reports USING GIN (reaction)")

    op.create_table(
        "submission_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("adr_report_id", postgresql.UUID(as_uuid=True), nullable=True),  # FK omitted: adr_reports PK is composite
        sa.Column("cartridge_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("regulatory_cartridges.id")),
        sa.Column("attempt_number", sa.Integer, nullable=False, server_default="1"),
        sa.Column("request_payload", postgresql.JSONB, nullable=True),
        sa.Column("response_status", sa.Integer, nullable=True),
        sa.Column("response_body", sa.Text, nullable=True),
        sa.Column("succeeded", sa.Boolean, nullable=True),
        sa.Column("attempted_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_submission_logs_report", "submission_logs", ["adr_report_id", "attempted_at"])


def downgrade():
    op.drop_table("submission_logs")
    op.drop_table("adr_reports")
    op.drop_table("regulatory_cartridges")
    op.drop_table("users")
    op.drop_table("organizations")
