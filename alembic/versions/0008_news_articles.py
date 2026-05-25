"""0008_news_articles

Revision ID: a3b4c5d6e7f9
Revises: f2a3b4c5d6e8
Create Date: 2026-05-25

Creates `news_articles` — daily market news deduplicated by source_url and
matched to ISINs by the News Agent (Chunk 3.2). sentiment_score / label are
left NULL for the Sentiment Agent (Chunk 3.3).
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

# revision identifiers, used by Alembic.
revision: str = "a3b4c5d6e7f9"
down_revision: str | None = "f2a3b4c5d6e8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "news_articles",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("isin", sa.String(length=12)),
        sa.Column("headline", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text()),
        sa.Column("source_name", sa.String(length=120), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("published_at", sa.TIMESTAMP(timezone=True)),
        sa.Column(
            "fetched_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("sentiment_score", sa.Numeric(5, 4)),
        sa.Column("sentiment_label", sa.String(length=8)),
        sa.Column("tags", JSONB()),
        sa.ForeignKeyConstraint(["isin"], ["stocks.isin"], ondelete="SET NULL"),
        sa.UniqueConstraint("source_url", name="news_articles_source_url_key"),
        sa.CheckConstraint(
            "sentiment_label IS NULL OR sentiment_label IN ('bull','bear','neutral')",
            name="sentiment_label_allowed",
        ),
    )
    op.create_index(
        "idx_news_isin_published",
        "news_articles",
        ["isin", sa.text("published_at DESC")],
    )
    op.create_index(
        "idx_news_published", "news_articles", [sa.text("published_at DESC")]
    )

    op.execute(
        "INSERT INTO schema_version (version_label, description, chunk_reference) "
        "VALUES ("
        "'0008_news_articles', "
        "'Created news_articles (deduped by source_url, ISIN-matched) for Phase 3.2', "
        "'phase-3-chunk-3.2'"
        ")"
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM schema_version WHERE version_label = '0008_news_articles'"
    )
    op.drop_index("idx_news_published", table_name="news_articles")
    op.drop_index("idx_news_isin_published", table_name="news_articles")
    op.drop_table("news_articles")
