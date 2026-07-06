"""Phase 4 agents: Source Scout, Source Trust, Episode Ranking.

Source Scout scans trusted Indian-finance channels (yt-dlp based fetcher,
injectable for tests). Source Trust scores each channel and gates it.
Episode Ranking picks the most current + viral episodes using channel-relative
velocity, freshness, and topic relevance.

Scores here are deterministic heuristics over real metadata (v1); an LLM
scorer can replace individual functions later without touching the pipeline.
"""
from __future__ import annotations

import json
import subprocess
import uuid
from datetime import UTC, datetime
from typing import Protocol

from .. import newsroom_reels_db as rdb
from . import newsroom_reels_queue as rq

# ---------------------------------------------------------------- seed data

SEED_SOURCES = [
    # core markets & investing
    {"name": "Moneycontrol", "query": "moneycontrol markets podcast"},
    {"name": "ET Markets", "query": "ET markets podcast india"},
    {"name": "CNBC-TV18", "query": "CNBC TV18 market analysis"},
    {"name": "Mint", "query": "mint india finance podcast"},
    {"name": "Value Research", "query": "value research mutual funds"},
    {"name": "Paisa Vaisa", "query": "paisa vaisa anupam gupta podcast"},
    {"name": "Finshots Daily", "query": "finshots daily"},
    {"name": "Capitalmind", "query": "capitalmind podcast"},
    {"name": "Yadnya Investment Academy", "query": "invest yadnya stock market"},
    {"name": "HDFC Securities", "query": "HDFC securities stock market updates"},
    {"name": "The Core Report", "query": "the core report india business"},
    {"name": "Motilal Oswal", "query": "motilal oswal indian market minutes"},
    {"name": "NDTV Profit", "query": "NDTV profit all you need to know markets"},
    {"name": "Sharekhan", "query": "sharekhan podcast markets"},
    {"name": "marketfeed", "query": "marketfeed aftermarket podcast"},
    {"name": "Stock Pathshala", "query": "stock pathshala"},
    {"name": "Angel One", "query": "angel one market movements"},
    {"name": "Goela House of Finance", "query": "goela house of finance"},
    # personal finance & money skills
    {"name": "CA Rachana Ranade", "query": "CA rachana ranade finance"},
    {"name": "Money Talks with Nikhil", "query": "money talks with nikhil kamath"},
    {"name": "Finance With Sharan", "query": "finance with sharan"},
    {"name": "Temperament", "query": "temperament money mind emotions podcast"},
    {"name": "MoneyShiksha", "query": "moneyshiksha brijesh"},
    {"name": "Personal Finance TV", "query": "personal finance TV india"},
    {"name": "Millennial Paisa", "query": "millennial paisa podcast"},
    # daily news / briefing
    {"name": "MarketBuzz CNBC", "query": "marketbuzz cnbc tv18 podcast"},
    {"name": "The Morning Brief ET", "query": "the morning brief economic times"},
    {"name": "Why Not Mint Money", "query": "why not mint money"},
    # broker / platform backed
    {"name": "Zerodha", "query": "zerodha please help me understand"},
    {"name": "Zerodha Educate", "query": "zerodha educate podcast"},
    {"name": "NSE India", "query": "NSE india shashakt niveshak podcast"},
    # high-signal interviews
    {"name": "Saurabh Mukherjea", "query": "saurabh mukherjea coffee investing podcast"},
    {"name": "The MM Show", "query": "the MM show finance podcast india"},
    {"name": "Neeraj Arora Money", "query": "neeraj arora money podcast"},
    # generic discovery sweeps
    {"name": "Indian market podcasts", "query": "indian stock market podcast latest"},
    {"name": "Indian business podcasts", "query": "indian business podcast finance"},
    {"name": "Indian founder/investor podcasts", "query": "indian investor podcast interview"},
    {"name": "Indian mutual fund podcasts", "query": "mutual fund india podcast latest"},
    {"name": "Indian personal finance podcasts", "query": "personal finance india podcast"},
]
_SEED_NAMES = {s["name"].lower() for s in SEED_SOURCES}

APPROVED_TOPICS = [
    "indian stock market", "nifty", "sensex", "nse", "bse", "sebi", "rbi",
    "indian economy", "sip", "mutual fund", "taxation", "tax", "budget",
    "rupee", "inflation", "earnings", "ipo", "banking", "nbfc", "fii", "dii",
    "smallcap", "small cap", "midcap", "mid cap", "largecap", "large cap",
    "investor psychology", "personal finance", "india", "indian", "pharma",
    "infra", "psu", "gst", "stock market", "stocks", "invest", "portfolio",
    "crore", "crorepati", "lakh", "sector", "valuation", "dividend",
    "quarterly results",
]
REJECT_TOPICS = [
    "crypto", "bitcoin", "forex signal", "price target", "sure shot", "jackpot",
    "guaranteed return", "us stocks only", "wall street only", "motivation",
    "get rich quick", "meme stock",
]


def _now() -> str:
    return datetime.now(UTC).isoformat()


def topic_relevance(text: str) -> int:
    """0-100: how strongly the text matches approved Indian-finance topics."""
    t = (text or "").lower()
    hits = sum(1 for k in APPROVED_TOPICS if k in t)
    rejects = sum(1 for k in REJECT_TOPICS if k in t)
    score = min(100, hits * 25) - rejects * 40
    return max(0, score)


# ---------------------------------------------------------------- fetcher

class EpisodeFetcher(Protocol):
    def search(self, query: str, limit: int) -> list[dict]:
        """Return raw episode dicts: id,title,url,channel,duration,view_count,
        upload_date (YYYYMMDD), description."""


class YtDlpFetcher:
    """Real fetcher using yt-dlp date-ordered search (no NSE scraping — YouTube
    metadata only, permitted retrieval path per the build spec)."""

    def search(self, query: str, limit: int = 5) -> list[dict]:
        # ytsearchdate is broken in yt-dlp 2026.06; plain ytsearch + the
        # ranking agent's freshness gate covers recency instead.
        cmd = ["python", "-m", "yt_dlp", f"ytsearch{limit}:{query}",
               "--dump-json", "--flat-playlist", "--no-warnings",
               "--extractor-args", "youtubetab:approximate_date"]
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        episodes = []
        for line in out.stdout.splitlines():
            try:
                episodes.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return episodes


# ---------------------------------------------------------------- Agent 5: Source Scout

def scan_sources(run_id: str, fetcher: EpisodeFetcher, per_source_limit: int = 5) -> dict:
    """Scan seed sources; store channels + fresh episodes."""
    found_sources, found_episodes = 0, 0
    for seed in SEED_SOURCES:
        try:
            raw = fetcher.search(seed["query"], per_source_limit)
        except Exception as e:  # noqa: BLE001 — a dead source never kills the scan
            rq.log(run_id, "source_scout", "reels.source.scan",
                   f"fetch failed for {seed['name']}: {e}", level="error")
            continue
        source_id = f"src-{uuid.uuid4().hex[:8]}"
        rdb.upsert("reels_sources", {
            "source_id": source_id, "name": seed["name"], "platform": "youtube",
            "channel_url": seed["query"], "last_scanned_at": _now(),
            "created_at": _now(),
        }, ["source_id"])
        found_sources += 1
        for ep in raw:
            title = ep.get("title") or ""
            # live streams: flaky downloads, hours long, poor clip material
            if ep.get("is_live") or ep.get("live_status") in ("is_live", "was_live") \
                    or "LIVE" in title.upper().split():
                continue
            if topic_relevance(title + " " + (ep.get("description") or "")) == 0:
                continue
            rdb.upsert("reels_episodes", {
                "episode_id": f"ep-{ep.get('id') or uuid.uuid4().hex[:10]}",
                "source_id": source_id, "run_id": run_id,
                "title": title, "url": ep.get("url") or ep.get("webpage_url"),
                "published_at": ep.get("upload_date"),
                "duration_sec": int(ep.get("duration") or 0),
                "views": int(ep.get("view_count") or 0),
                "status": "discovered", "created_at": _now(),
            }, ["episode_id"])
            found_episodes += 1
    rq.log(run_id, "source_scout", "reels.source.scan",
           f"scan done: {found_sources} sources, {found_episodes} episodes")
    return {"sources": found_sources, "episodes": found_episodes}


# ---------------------------------------------------------------- Agent 6: Source Trust

def score_source(source_id: str) -> dict:
    """Heuristic trust scoring over the source's stored episodes."""
    src = rdb.query_one("SELECT * FROM reels_sources WHERE source_id=?", (source_id,))
    eps = rdb.query_all("SELECT * FROM reels_episodes WHERE source_id=?", (source_id,))
    texts = " ".join((e["title"] or "") for e in eps)

    authority = 85 if (src["name"] or "").lower() in _SEED_NAMES else 55
    india_rel = topic_relevance(texts) if eps else 0
    sensational = sum(1 for k in REJECT_TOPICS if k in texts.lower()) * 15
    avg_dur = (sum(e["duration_sec"] or 0 for e in eps) / len(eps)) if eps else 0
    edu_density = 80 if avg_dur >= 600 else 55 if avg_dur >= 180 else 30
    quality = 75  # placeholder until Claude Video source-watch (Phase 5) refines it
    engagement = 70 if any((e["views"] or 0) > 10_000 for e in eps) else 50
    yield_score = min(100, len(eps) * 20)
    compliance_risk = min(100, sensational + (40 if india_rel < 40 else 0))

    source_score = round(
        authority * .25 + india_rel * .25 + quality * .10 + edu_density * .15 +
        engagement * .10 + yield_score * .15 - sensational * .5)
    source_score = max(0, min(100, source_score))
    passed = int(source_score >= 75 and india_rel >= 80 and compliance_risk <= 35)

    scores = {
        "authority_score": authority, "india_relevance_score": india_rel,
        "audio_video_quality_score": quality, "educational_density_score": edu_density,
        "engagement_quality_score": engagement, "historical_clip_yield_score": yield_score,
        "sensationalism_penalty": sensational, "compliance_risk_score": compliance_risk,
        "source_score": source_score, "passed": passed,
    }
    rdb.upsert("reels_sources", {"source_id": source_id, **scores}, ["source_id"])
    return scores


# ---------------------------------------------------------------- Agent 7: Episode Ranking

def _enrich_from_meta(e: dict) -> dict:
    """Flat search results lack upload_date/full description — fetch once for
    episodes that are otherwise eligible, so freshness is measured, not
    defaulted."""
    from .newsroom_reels_watch import fetch_video_meta
    try:
        meta = fetch_video_meta(e["url"])
    except Exception:  # noqa: BLE001 — enrichment is best-effort
        return e
    e = dict(e)
    e["published_at"] = e["published_at"] or meta.get("upload_date")
    e["views"] = meta.get("view_count") or e["views"]
    e["_full_text"] = f"{e['title']} {meta.get('description') or ''}"
    with rdb.connect() as c:
        c.execute("UPDATE reels_episodes SET published_at=?, views=? WHERE episode_id=?",
                  (e["published_at"], e["views"], e["episode_id"]))
    return e


def rank_episodes(run_id: str, enrich_top: int = 15) -> list[dict]:
    """Score episodes of passed sources; relative-to-channel velocity + freshness."""
    eps = rdb.query_all(
        "SELECT e.*, s.source_score, s.passed AS source_passed FROM reels_episodes e "
        "JOIN reels_sources s ON s.source_id = e.source_id WHERE e.run_id=?", (run_id,))
    # enrich the most promising candidates with real upload dates + descriptions
    eligible = sorted((e for e in eps if e["source_passed"]),
                      key=lambda e: (e["views"] or 0), reverse=True)[:enrich_top]
    enriched = {e["episode_id"]: _enrich_from_meta(e) for e in eligible}
    eps = [enriched.get(e["episode_id"], e) for e in eps]
    now = datetime.now(UTC)
    by_source: dict[str, list[dict]] = {}
    for e in eps:
        by_source.setdefault(e["source_id"], []).append(e)

    ranked = []
    for source_eps in by_source.values():
        baseline = max(1.0, sum((e["views"] or 0) for e in source_eps) / len(source_eps))
        for e in source_eps:
            age_h = 168.0
            if e["published_at"]:
                try:
                    dt = datetime.strptime(str(e["published_at"]), "%Y%m%d").replace(tzinfo=UTC)
                    age_h = max(1.0, (now - dt).total_seconds() / 3600)
                except ValueError:
                    pass
            vph = (e["views"] or 0) / age_h
            rel_perf = min(2.0, (e["views"] or 0) / baseline)
            freshness = 100 if age_h <= 24 else 80 if age_h <= 48 else 50 if age_h <= 168 else 0
            hook = 70 if any(c in (e["title"] or "") for c in "?!") or any(
                w in (e["title"] or "").lower() for w in ("why", "how", "mistake", "truth")) else 50
            from .newsroom_reels_llm import llm_episode_relevance
            topic_rel = llm_episode_relevance(
                e["title"] or "", e.get("_full_text") or "")
            if topic_rel is None:   # LLM down -> keyword fallback
                topic_rel = topic_relevance(e.get("_full_text") or e["title"] or "")
            # vph/5 calibrated to the Indian finance niche: 500 views/hr = max
            viral = round(freshness * .35 + rel_perf * 50 * .25 +
                          min(100, vph / 5) * .15 + hook * .15 + topic_rel * .10)
            passed = (viral >= 70 and topic_rel >= 80 and
                      (e["source_score"] or 0) >= 75 and e["source_passed"])
            with rdb.connect() as c:
                c.execute(
                    "UPDATE reels_episodes SET views_per_hour=?, episode_viral_score=?, "
                    "topic_relevance_score=?, status=? WHERE episode_id=?",
                    (round(vph, 2), viral, topic_rel,
                     "ranked_pass" if passed else "ranked_fail", e["episode_id"]))
            ranked.append({"episode_id": e["episode_id"], "episode_viral_score": viral,
                           "topic_relevance_score": topic_rel, "passed": bool(passed)})
    ranked.sort(key=lambda r: r["episode_viral_score"], reverse=True)
    rq.log(run_id, "episode_ranking", "reels.episode.rank",
           f"ranked {len(ranked)}: {sum(r['passed'] for r in ranked)} passed")
    return ranked


# ---------------------------------------------------------------- queue handlers

async def _handle_source_scan(job: dict) -> None:
    run_id = job["run_id"]
    scan_sources(run_id, YtDlpFetcher())
    rq.enqueue("reels.source.score", run_id=run_id)


async def _handle_source_score(job: dict) -> None:
    run_id = job["run_id"]
    for s in rdb.query_all("SELECT source_id FROM reels_sources"):
        score_source(s["source_id"])
    rq.enqueue("reels.episode.rank", run_id=run_id)


async def _handle_episode_rank(job: dict) -> None:
    rank_episodes(job["run_id"])


rq.register("reels.source.scan", _handle_source_scan)
rq.register("reels.source.score", _handle_source_score)
rq.register("reels.episode.rank", _handle_episode_rank)
