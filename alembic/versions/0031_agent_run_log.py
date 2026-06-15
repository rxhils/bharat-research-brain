"""0031_agent_run_log

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-06-16

Lightweight live-observability heartbeat for the agentic pipeline. As each agent
runs in the nightly job it upserts its row here (status / progress / one-line headline
/ timing), keyed (run_id, agent_name). The Maven dashboard's Agent Activity board
polls this. Does NOT touch F+ or the scores themselves — pure status telemetry.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a7b8c9d0e1f2"
down_revision: str | None = "f6a7b8c9d0e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "agent_run_log",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("run_id", sa.String(length=40), nullable=False),
        sa.Column("agent_name", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=12), nullable=False),
        sa.Column("progress_current", sa.Integer(), nullable=True),
        sa.Column("progress_total", sa.Integer(), nullable=True),
        sa.Column("headline_output", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column("offline_reason", sa.Text(), nullable=True),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("finished_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.BigInteger(), nullable=True),
        sa.Column(
            "updated_at", sa.TIMESTAMP(timezone=True), nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "status IN ('running','done','waiting','offline','error')",
            name="agent_run_log_status",
        ),
        sa.UniqueConstraint("run_id", "agent_name", name="agent_run_log_run_agent"),
    )
    op.create_index("idx_agent_run_log_run", "agent_run_log", ["run_id"])
    op.execute(
        "INSERT INTO schema_version (version_label, description, chunk_reference) "
        "VALUES ("
        "'0031_agent_run_log', "
        "'Live agent-run heartbeat for the Maven dashboard Agent Activity board', "
        "'chunk-5.3-maven'"
        ")"
    )


def downgrade() -> None:
    op.execute("DELETE FROM schema_version WHERE version_label = '0031_agent_run_log'")
    op.drop_index("idx_agent_run_log_run", table_name="agent_run_log")
    op.drop_table("agent_run_log")
