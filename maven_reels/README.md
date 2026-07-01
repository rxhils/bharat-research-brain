# Maven Reels — retention-first viral market explainers

A **second, independent** content pipeline alongside the carousel pipeline
(`maven_instagram/`). Carousel = clean market education. **Reels = high-retention,
viral-style 20–35s explainers** of one important Indian-market event.

It **never modifies `maven_instagram/`** — it reuses that pipeline's compliance
scanner + brand by read-only import. Artifacts live under `outputs/maven_reels/<date>/`.

## Pipeline (22 nodes; premium UI names in the Newsroom OS "Reels" section)
```
Closing Bell → Claude Conductor → Market Sentinel → Viral Fit Gate → Angle Studio
→ Hook Lab → Script Room → Retention Editor → Storyboard → Visual Director
→ Scene Studio → Voice Studio → Subtitle Engine → Cut Room → Cover Frame Studio
→ Caption Desk → Compliance Shield → Reel Auditor → Publish Gate → Reels Courier
→ Signal Tracker → Run Vault
```

### The reel-specific pieces
- **Viral Fit Gate** (`step02_viral_fit`): the most *important* story ≠ the best
  *reel*. Scores every story on Importance/Curiosity/Emotional/Simplicity/Visual/
  Shareability/Retail-relevance (weighted toward scroll-stop) and picks the best reel.
- **Hook Lab** (`step04_hooks`): always emits a hook in 7 buckets (curiosity/shock/
  contrarian/simple/data/myth/question), scores, picks the strongest.
- **Retention Editor** (`step06_retention`): cuts filler openers ("Today we're
  going to…"), enforces <35s, hook-in-line-1, a visual beat ~every 3s.
- **Cover Frame Studio** (`step13_cover`): a dedicated `cover.jpg` grid cover.
- **Signal Tracker** (`analytics.py`): reel metrics — 3s retention, watch time,
  replays, saves, shares, follows — north star = watched-past-3s + rewatch + save/share.

## Media approach (locked)
- **Visuals:** premium Higgsfield stills (`nano_banana_pro`, 9:16) + **ffmpeg
  motion** (Ken-Burns + crossfades) + **crisp animated/burned captions**. No AI-video look.
- **Voice:** Higgsfield TTS (`text2speech_v2_*`). **Music:** original ffmpeg synth.
- **Publish:** Composio `INSTAGRAM_POST_IG_USER_MEDIA` `media_type=REELS`.

## Run (deterministic prepare — no paid media)
```bash
# 1) drop a reel research artifact at outputs/maven_reels/<date>/01_research.json
python -m maven_reels.pipeline.orchestrator prepare --date <date>
```
This runs research→viral-fit→angle→hooks→script→retention→storyboard→visual-
direction→scene-jobs→subtitles→cover-job→caption→compliance→reel-auditor and
writes all the JSON artifacts. The external steps (Higgsfield scenes/voiceover,
ffmpeg cut, Composio Reels publish) run in the Claude Code conductor.

## Honesty
- Educational only; no advice/targets/fake numbers (reuses `compliance.py`).
- Publishing needs the Claude Code conductor (MCP); the backend marks it
  `requires_conductor` and never shows "published" without a real media id.
- `maven_instagram/**` is untouched.
```
