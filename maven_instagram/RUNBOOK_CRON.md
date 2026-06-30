# Maven daily 5 PM IST cron — runbook

This is the exact procedure the scheduled cloud agent follows every day at
**17:00 IST (11:30 UTC)**. It is the same workflow as the manual run, plus a
music Story. It **auto-publishes only when strict gates pass**; otherwise it
holds and notifies.

## Pre-flight (fail loud, do not fake)
1. Resolve today's date in IST (`Asia/Kolkata`). Confirm it is a trading day
   (Mon–Fri, not an NSE holiday). If the market is closed today → **stop**,
   notify "market closed today, no post".
2. Verify MCPs are reachable: Higgsfield `generate_image`/`balance`, and
   Composio Instagram tools (`INSTAGRAM_GET_USER_INFO` → must be `try.maven`,
   BUSINESS). If either is missing in the headless session → **stop & notify**.

## Steps
1. **Research** (IndianMarketResearchAgent): live web scan for *today's* top 3.
   - Cross-check closing levels against ≥2 Tier-A sources. Verify the weekday.
   - **Never reuse yesterday's numbers.** If today's official close is not yet
     verifiable from a primary, correctly-dated source → **hold & notify**
     ("today's close not yet verifiable, will not publish stale data").
   - Keep only stories with importance ≥7 AND confidence ≥8. Need ≥1; aim for 3.
2. **Content plan** → 3 slides (refine copy: complete, premium, no ellipses).
3. **Creative direction** → pick the hybrid dark-cover + light-cards system.
4. **Images**: Higgsfield `nano_banana_pro`, 4:5, one per slide. Download,
   post-process to clean 1080×1350 JPEG. Re-render any slide that invents
   unsourced numbers (charts show *direction*, not fabricated decimals).
5. **Caption + hashtags** (10–18). Disclaimer required. Compliance scan must be
   clean (no buy/sell/hold/target/hype).
6. **Quality gate**: content ≥90, design ≥90, compliance ≥95. Provide an
   honest aesthetic score after visually reviewing the renders. If BLOCKED →
   fix the failing part (do **not** re-run research if only design/caption
   fails) and re-gate.
7. **Story video + music**: `step9_story_video.build_story_video(date)` →
   1080×1920 MP4 of the 3 slides with the original ffmpeg ambient track baked
   in (no licensed/third-party audio).
8. **Publish (only if gate PUBLISH_OK and data verified):**
   - Feed carousel: upload 3 JPEGs (Composio workbench `upload_local_file` →
     s3key) → `INSTAGRAM_CREATE_CAROUSEL_CONTAINER` (caption+hashtags) →
     `INSTAGRAM_POST_IG_USER_MEDIA_PUBLISH` → permalink.
   - Story: upload `story.mp4` → `INSTAGRAM_POST_IG_USER_MEDIA`
     (`media_type=STORIES`, video) → publish (wait up to 180s).
9. **Record + notify**: save `_final_output.json`; push/email the carousel
   permalink + story status (or the hold reason).

## Hard rules (inherited from CLAUDE.md)
- Educational only. No advice, no price targets, no hype. Cite sources.
- No fabricated numbers — if a figure isn't sourced, don't show it.
- Every post ends with the disclaimer.

## Mode
- Default: **auto-publish on strict gate-pass.**
- To require manual approval instead, change the routine prompt to: "build
  everything, save artifacts, send the 3 slides + caption for approval, and DO
  NOT publish until I reply 'publish'."
- Pause/stop: disable or delete the trigger (it is listed in your routines).
