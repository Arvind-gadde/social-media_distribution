"""Add orchestration tables: agent_runs, content_insights

Revision ID: 002_add_orchestration
Revises: 001_add_content_agent
Create Date: 2026-03-19 10:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON, UUID

revision = "002_add_orchestration"
down_revision = "001_add_content_agent"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── agent_runs ────────────────────────────────────────────────────────────
    op.create_table(
        "agent_runs",
        sa.Column("id",              UUID(as_uuid=True), primary_key=True),
        sa.Column("triggered_by",    sa.String(50),  nullable=False, server_default="celery_beat"),
        sa.Column("status",          sa.String(20),  nullable=False, server_default="running"),

        # Per-stage timing
        sa.Column("scout_duration_s",    sa.Float(), nullable=True),
        sa.Column("analyst_duration_s",  sa.Float(), nullable=True),
        sa.Column("checker_duration_s",  sa.Float(), nullable=True),
        sa.Column("creative_duration_s", sa.Float(), nullable=True),

        # Counts
        sa.Column("items_fetched",      sa.Integer(), nullable=False, server_default="0"),
        sa.Column("items_new",          sa.Integer(), nullable=False, server_default="0"),
        sa.Column("items_scored",       sa.Integer(), nullable=False, server_default="0"),
        sa.Column("items_fact_checked", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("items_generated",    sa.Integer(), nullable=False, server_default="0"),
        sa.Column("gap_signals_found",  sa.Integer(), nullable=False, server_default="0"),

        # Error log
        sa.Column("stage_errors", JSON, nullable=True),

        # Timestamps
        sa.Column("started_at",  sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_agent_runs_started", "agent_runs", ["started_at"])

    # ── content_insights ──────────────────────────────────────────────────────
    op.create_table(
        "content_insights",
        sa.Column("id",              UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "content_item_id", UUID(as_uuid=True),
            sa.ForeignKey("content_items.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),

        # Virality signals
        sa.Column("virality_score",    sa.Float(),   nullable=False, server_default="0.0"),
        sa.Column("cross_source_count",sa.Integer(), nullable=False, server_default="1"),
        sa.Column("trend_velocity",    sa.Float(),   nullable=False, server_default="0.0"),
        sa.Column("sentiment_breakdown", JSON,       nullable=True),

        # Value gap
        sa.Column("is_value_gap",    sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("gap_explanation", sa.Text(),    nullable=True),
        sa.Column("suggested_angle", sa.Text(),    nullable=True),

        # B-Roll
        sa.Column("broll_assets", JSON, nullable=True),

        # Fact-check
        sa.Column("fact_check_passed",     sa.Boolean(), nullable=True),
        sa.Column("fact_check_confidence", sa.Float(),   nullable=True),
        sa.Column("flagged_claims", JSON, nullable=True),

        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_content_insights_item", "content_insights", ["content_item_id"])
    op.create_index("ix_content_insights_gap",  "content_insights", ["is_value_gap"])


def downgrade() -> None:
    op.drop_table("content_insights")
    op.drop_table("agent_runs")
