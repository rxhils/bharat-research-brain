# Maven daily Reel cron — runbook

The exact procedure the scheduled cloud agent follows every day. Same engine as
a manual "Run Reel via Claude": the deterministic pipeline runs in Python, and
the animated clips + voiceover are generated through the **Higgsfield MCP**
(the account already connected to Claude — no API key, no CLI login). It
**builds the reel automatically and HOLDS for approval by default**; it does not
auto-publish unless the operator switched the routine to auto-publish mode.

## Pre-flight (fail loud, do not fake)
1. Resolve today's date in IST (`Asia/Kolkata`). Data-mode is fine any day —
   intraday during market hours, post-market after close, latest-trading-day on
   weekends/holidays. Do NOT block just because the market is closed.
2. Verify the Higgsfield MCP is reachable in this session (`balance` /
   `models_explore`). If it is **absent in this headless run → stop & notify**
   ("Higgsfield MCP not available to the scheduled session; reel not generated").
   Composio is only needed if publishing (see step 9).

## Steps (run from repo root `C:\Users\fazea\bharat research brain`)
1. **Create the job + run the backend prep (deterministic, free).**
   ```
   python -c "from maven-newsroom.backend.app.services import reel_studio as r; import json; print(json.dumps(r.create_reel_job(source='daily_cron')))"
   ```
   (or run the pipeline modules directly). This runs backend research
   (`step1_research_backend`), creative brief, 25-hook Hook Lab, script +
   retention edit, renderer selector, creative director, shot planner, model
   router (cheapest-suitable model per scene), and the Higgsfield prompt builder.
   It stops at `awaiting_generation_confirmation` with everything planned. Note
   the `job_id`.
   - Research must be **fresh** and **sourced** (every story has a URL). If no
     usable story is found → **hold & notify**, do not fabricate.
2. **Generate the animated clips through the Higgsfield MCP.** Read
   `outputs/maven_reels/<job_id>/11_higgsfield_prompts.json` (per-shot prompts)
   and `10_model_router.json` (per-shot model). For each shot call Higgsfield
   `generate_video` (text-to-video, 9:16, ~4s, `sound=off`), using the router's
   model; preflight `get_cost:true` first (free). Poll `job_display`; download
   each result to `outputs/maven_reels/<job_id>/higgsfield_clips/shot_0N.mp4`.
   - Prompts already forbid readable/fake text — do not add any.
   - Stay within the per-reel credit ceiling (`HIGGSFIELD_MAX_CREDITS_PER_REEL`).
3. **Voiceover through the Higgsfield MCP.** Read the narration from
   `06_script_edited.json`, call `generate_audio` (`seed_audio`), download,
   convert WAV→MP3 with ffmpeg → `outputs/maven_reels/<job_id>/voiceover.mp3`.
4. **Record + assemble + audit (Python, free).**
   ```
   record_results(job_id, [...per-clip metadata, verified on disk...])
   reel_studio.assemble_and_audit(job_id)
   ```
   This runs the Scene Quality Inspector, the ffmpeg Final Reel Assembler
   (stitches clips + burns subtitles + mixes voiceover + music/SFX → `reel.mp4`
   + `cover.jpg`), the 14-gate viral auditor, then ingests + marks latest.
5. **Gate.** Production gates: hook ≥90, story ≥85, animation ≥90, visual ≥90,
   retention ≥90, teaching ≥85, compliance ≥95, freshness ≥95. If BLOCKED, fix
   only the failing node (e.g. re-run one scene or the subtitle/voiceover step)
   and re-audit — do NOT re-run research if only a downstream node failed.
6. **Hold for approval (default) + notify.** Save artifacts. Push/email: the
   `job_id`, the auditor verdict, and the Reel Review link
   (`/reels/review/<job_id>`). **Do not publish.** The operator reviews the reel
   in the localhost UI and clicks Approve & Publish when happy.

## Publish (ONLY in auto-publish mode, and ONLY if the gate passes)
If the routine is switched to auto-publish: verify Composio Instagram is
reachable (`INSTAGRAM_GET_USER_INFO` → must be `try.maven`, BUSINESS). Upload
`reel.mp4` to a clean public URL (Higgsfield `media_upload`/`media_confirm` →
CDN URL), then `INSTAGRAM_POST_IG_USER_MEDIA` (`media_type=REELS`, `video_url`,
caption+hashtags) → `INSTAGRAM_POST_IG_USER_MEDIA_PUBLISH` → fetch the permalink
via `INSTAGRAM_GET_IG_MEDIA`. Only mark published on a real media id/permalink —
never fake it.

## Hard rules (inherited from CLAUDE.md)
- Educational only. No advice, no price targets, no hype. Cite sources.
- No fabricated numbers — if a figure isn't sourced, don't show it. All real
  numbers live in the burned overlays, never inside the generated footage.
- Every reel ends with the Maven disclaimer/CTA.
- Never touch `maven_instagram/**` or the carousel pipeline.

## Mode
- Default: **build + hold for approval** (safe while we keep improving Reels).
- To auto-publish on strict gate-pass, change the routine prompt to: "…after the
  auditor passes all gates, publish the reel to @try.maven via Composio and
  send me the permalink."
- Pause/stop: disable or delete the routine (listed in your routines).
