# Maven — Daily Instagram Market Digest Pipeline

A modular, rerunnable workflow that produces **one premium, educational
Instagram carousel per day** about the Indian stock market for the brand
**Maven / trymaven.in** (`@try.maven`).

Each post = exactly **3 slides**, one per the day's top-3 most important market
stories. Output is informational only — **never advice**, no buy/sell/hold, no
price targets, no hype, no fake numbers, every claim sourced.

---

## Pipeline (8 steps)

| # | Step | Module | Output artifact |
|---|------|--------|-----------------|
| 1 | Market research (top 3, gated by importance≥7 & confidence≥8) | `step1_research.py` (+ research agent) | `01_research.json` |
| 2 | Content plan (3 slides) | `step2_content_plan.py` | `02_content_plan.json` |
| 3 | Creative direction (3 concepts → pick 1) | `step3_creative_direction.py` | `03_creative_direction.json` |
| 4 | Image prompts + post-processing | `step4_images.py` | `04_images.json`, `slide_*.png/jpg` |
| 5 | Caption / description | `step5_caption.py` | `05_caption.json` |
| 6 | Hashtags (10–18) | `step6_hashtags.py` | `06_hashtags.json` |
| 7 | Quality gate (content≥90, design≥90, compliance≥95) | `step7_quality_check.py` | `07_quality_check.json` |
| 8 | Publish carousel to Instagram | `step8_publish.py` | `08_publish.json` |

Artifacts land in `outputs/maven_instagram/<YYYY-MM-DD>/`. A `_state.json`
tracks which steps are done so any step can be rerun independently.

## The MCP boundary (important)

The two **network** actions are performed by MCP servers that are available to
the **agent runtime** (Claude Code), not to a bare Python process:

- **Image generation** → **Higgsfield MCP** `generate_image`, model
  `nano_banana_pro` (this *is* "NanoBanana"; best for text/diagrams).
- **Publishing** → **Composio MCP** Instagram tools
  (`INSTAGRAM_POST_IG_USER_MEDIA` → `INSTAGRAM_CREATE_CAROUSEL_CONTAINER` →
  `INSTAGRAM_POST_IG_USER_MEDIA_PUBLISH`).

So `python -m maven_instagram.pipeline.orchestrator prepare` runs all the
**deterministic** work (research validation/gating, content, creative, caption,
hashtags, image-prompt building, post-processing, quality scoring, publish
payload building) and stops before the live calls. The agent then runs the two
MCP actions and feeds results back via `state.save_artifact` /
`step8_publish.record_result`. To run it fully headless later, implement an
`Executor` (see `mcp_adapter.py`) wired to the Higgsfield + Composio/Instagram
APIs with your own keys.

## Run

```bash
# deterministic prepare phase (no network, no credits, no publish)
python -m maven_instagram.pipeline.orchestrator prepare --date 2026-06-29

# individual steps (rerun any one without redoing the rest)
python -m maven_instagram.pipeline.orchestrator content  --date 2026-06-29
python -m maven_instagram.pipeline.orchestrator caption  --date 2026-06-29
python -m maven_instagram.pipeline.orchestrator quality  --date 2026-06-29 --aesthetic-score 95
```

Requires Python 3.11+ and `pillow` (image post-processing). No other deps.

## Hard guarantees baked into the code

- **Never regenerate research if only design fails** — steps are isolated by
  artifact; rerun `images`/`creative` without touching `01_research.json`.
- **Never regenerate images if only caption fails** — `caption` reads research +
  content plan only.
- **Never publish without validation** — `step8_publish.preflight()` refuses
  unless the quality gate passed *and* a human confirmation flag is set.
- **No fake numbers** — only sourced figures appear; charts that would require
  unsourced precision are rendered as direction, not invented decimals.
- **Compliance scan** — every text artifact is scanned for banned advisory
  language (`compliance.py`); a disclaimer is required in the caption.

## Image hosting for publishing

Instagram fetches carousel images by **public HTTPS URL with no query string**
(or via an uploaded file ref). Higgsfield returns signed URLs (query strings →
rejected), so slides are downloaded, post-processed to clean 1080×1350 JPEGs,
and hosted via one of (`mcp_adapter.HOSTING_OPTIONS`):
- `maven-site/public/ig/<date>/slide_N.jpg` on Vercel → `trymaven.in/ig/...`
- Composio `child_image_files` (s3key) upload path.
