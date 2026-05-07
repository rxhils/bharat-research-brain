"""0002_seed_indices

Revision ID: b800cd761633
Revises: 7726337f67ac
Create Date: 2026-05-08 02:18:53.023718

Seeds the 15 indices the universe layer tracks: 4 broad
(Nifty 50/100/200/500) and 11 sectoral. Membership is populated
separately by Chunk 1.2 (Universe Agent).
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b800cd761633'
down_revision: str | None = '7726337f67ac'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_INDICES_TABLE = sa.Table(
    "indices",
    sa.MetaData(),
    sa.Column("index_code", sa.String(32)),
    sa.Column("index_name", sa.String(120)),
    sa.Column("index_type", sa.String(16)),
    sa.Column("description", sa.Text()),
)


_SEED_ROWS: list[dict[str, str]] = [
    # Broad indices
    {
        "index_code": "NIFTY50",
        "index_name": "Nifty 50",
        "index_type": "broad",
        "description": "India's flagship benchmark — 50 largest, most liquid stocks across sectors.",
    },
    {
        "index_code": "NIFTY100",
        "index_name": "Nifty 100",
        "index_type": "broad",
        "description": "Top 100 stocks by free-float market cap from Nifty 500 universe.",
    },
    {
        "index_code": "NIFTY200",
        "index_name": "Nifty 200",
        "index_type": "broad",
        "description": "Top 200 stocks by free-float market cap; large + mid cap blend.",
    },
    {
        "index_code": "NIFTY500",
        "index_name": "Nifty 500",
        "index_type": "broad",
        "description": "Broadest investable universe — top 500 stocks by free-float market cap.",
    },
    # Sectoral indices
    {
        "index_code": "NIFTYBANK",
        "index_name": "Nifty Bank",
        "index_type": "sector",
        "description": "12 most liquid and large-capitalised banking stocks.",
    },
    {
        "index_code": "NIFTYIT",
        "index_name": "Nifty IT",
        "index_type": "sector",
        "description": "Top 10 IT companies by free-float market cap.",
    },
    {
        "index_code": "NIFTYAUTO",
        "index_name": "Nifty Auto",
        "index_type": "sector",
        "description": "Top 15 stocks from auto manufacturers, ancillaries, and tyres.",
    },
    {
        "index_code": "NIFTYPHARMA",
        "index_name": "Nifty Pharma",
        "index_type": "sector",
        "description": "Top 20 pharma manufacturers and healthcare service providers.",
    },
    {
        "index_code": "NIFTYFMCG",
        "index_name": "Nifty FMCG",
        "index_type": "sector",
        "description": "15 large-cap FMCG companies — food, personal care, household.",
    },
    {
        "index_code": "NIFTYMETAL",
        "index_name": "Nifty Metal",
        "index_type": "sector",
        "description": "Top 15 metal & mining companies including PSU and private.",
    },
    {
        "index_code": "NIFTYENERGY",
        "index_name": "Nifty Energy",
        "index_type": "sector",
        "description": "Top 10 stocks from energy — oil & gas, power, refining.",
    },
    {
        "index_code": "NIFTYREALTY",
        "index_name": "Nifty Realty",
        "index_type": "sector",
        "description": "Top 10 real estate development and construction stocks.",
    },
    {
        "index_code": "NIFTYFINSERVICE",
        "index_name": "Nifty Financial Services",
        "index_type": "sector",
        "description": "Banks + non-banking financials + insurance + housing finance.",
    },
    {
        "index_code": "NIFTYMEDIA",
        "index_name": "Nifty Media",
        "index_type": "sector",
        "description": "Top 15 stocks across media, broadcasting, publishing, entertainment.",
    },
    {
        "index_code": "NIFTYPSUBANK",
        "index_name": "Nifty PSU Bank",
        "index_type": "sector",
        "description": "Public Sector Bank stocks listed on NSE.",
    },
]


_INDEX_CODES = tuple(r["index_code"] for r in _SEED_ROWS)


def upgrade() -> None:
    op.bulk_insert(_INDICES_TABLE, _SEED_ROWS)

    # Operational migration log — final op of every migration per spec §3.3.
    op.execute(
        "INSERT INTO schema_version (version_label, description, chunk_reference) "
        "VALUES ("
        "'0002_seed_indices', "
        "'Seeded 15 indices: 4 broad (Nifty 50/100/200/500) + 11 sectoral', "
        "'phase-1-chunk-1.1'"
        ")"
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM schema_version WHERE version_label = '0002_seed_indices'"
    )
    op.execute(
        "DELETE FROM indices WHERE index_code IN ("
        + ", ".join(f"'{c}'" for c in _INDEX_CODES)
        + ")"
    )
