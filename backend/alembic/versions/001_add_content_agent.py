"""Add content agent tables

Revision ID: 001_add_content_agent
Revises: 0d57487546e2
Create Date: 2026-03-15 12:00:00.000000
"""
from __future__ import annotations
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON, UUID

revision = "001_add_content_agent"
down_revision = "0d57487546e2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "content_items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("source_key",     sa.String(100),  nullable=False),
        sa.Column("source_label",   sa.String(200),  nullable=False),
        sa.Column("source_url",     sa.String(2000), nullable=True, unique=True),
        sa.Column("title",          sa.Text(),        nullable=False),
        sa.Column("raw_content",    sa.Text(),        nullable=True),
        sa.Column("author",         sa.String(200),   nullable=True),
        sa.Column("published_at",   sa.DateTime(timezone=True), nullable=True),
        sa.Column("summary",        sa.Text(),        nullable=True),
        sa.Column("key_points",     JSON,             nullable=True),
        sa.Column("category",       sa.String(50),    nullable=False, server_default="other"),
        sa.Column("relevance_score",sa.Float(),       nullable=False, server_default="0.0"),
        sa.Column("is_processed",   sa.Boolean(),     nullable=False, server_default="false"),
        sa.Column("is_trending",    sa.Boolean(),     nullable=False, server_default="false"),
        sa.Column("fetched_at",     sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_content_items_source_key",   "content_items", ["source_key"])
    op.create_index("ix_content_items_category",     "content_items", ["category"])
    op.create_index("ix_content_items_is_processed", "content_items", ["is_processed"])
    op.create_index("ix_content_items_fetched_at",   "content_items", ["fetched_at"])
    op.create_index("ix_content_items_relevance",    "content_items", ["relevance_score", "fetched_at"])

    op.create_table(
        "generated_posts",
        sa.Column("id",              UUID(as_uuid=True), primary_key=True),
        sa.Column("content_item_id", UUID(as_uuid=True),
                  sa.ForeignKey("content_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id",         UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("platform",        sa.String(30),  nullable=False),
        sa.Column("hook",            sa.Text(),       nullable=True),
        sa.Column("caption",         sa.Text(),       nullable=True),
        sa.Column("hashtags",        JSON,            nullable=True),
        sa.Column("call_to_action",  sa.Text(),       nullable=True),
        sa.Column("script_outline",  sa.Text(),       nullable=True),
        sa.Column("thread_tweets",   JSON,            nullable=True),
        sa.Column("engagement_tips", JSON,            nullable=True),
        sa.Column("created_at",      sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_generated_posts_content_item_id", "generated_posts", ["content_item_id"])
    op.create_index("ix_generated_posts_user_id",         "generated_posts", ["user_id"])


def downgrade() -> None:
    op.drop_table("generated_posts")
    op.drop_table("content_items")
