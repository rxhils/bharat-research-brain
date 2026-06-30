# Maven Newsroom OS — Phase 2 (Frontend) handoff

Phase 1 (backend) is **done, verified, and live**. This doc is the complete
contract so the Next.js dashboard can be built in one focused session without
re-discovering anything.

## How to start Phase 2 (paste into a fresh session)
> Build the Maven Newsroom OS frontend in `maven-newsroom/frontend` (Next.js 14
> App Router + TypeScript + Tailwind + Framer Motion + React Flow + Recharts +
> lucide-react). The FastAPI backend is already built and running — follow
> `maven-newsroom/PHASE2_FRONTEND.md` exactly for the API contract, node
> registry, design tokens, and page/component plan. Do not modify the backend or
> the `maven_instagram` pipeline. Honesty rules in the doc are mandatory.

## Backend connection
- Base URL via env: `NEXT_PUBLIC_API_BASE` (default `http://localhost:8000`).
- Start backend: `cd maven-newsroom/backend && python -m uvicorn app.main:app --port 8000 --reload`
  (currently running on **8001** in the prior session due to a transient stuck
  socket; a fresh boot uses 8000).
- CORS already allows `localhost:3000`.

## API contract (all verified)
| Method | Path | Returns |
|---|---|---|
| GET | `/api/health` | `{status, db:{jobs,nodes,events,artifacts}, time_ist}` |
| GET | `/api/meta` | `{product, subtitle, date_ist, market:{open,reason}, next_run, run_name, trigger_agent, thresholds}` |
| GET | `/api/nodes` | `{nodes:[…17…], graph_order:[…16…], class_labels}` |
| GET | `/api/jobs` | `{jobs:[{…, scores, thumbnails:["slide_1.jpg",…]}]}` |
| GET | `/api/jobs/{id}` | job + `scores` + `nodes[]` + `artifact_count` |
| GET | `/api/jobs/{id}/nodes` | `{nodes:[…]}` |
| GET | `/api/jobs/{id}/events?after_seq=` | `{events:[…]}` (poll fallback for SSE) |
| GET | `/api/jobs/{id}/artifacts` | `{artifacts:[…]}` |
| GET | `/api/jobs/{id}/scores` | scores row |
| GET | `/api/jobs/{id}/artifact/{name}` | JSON inline, or image/video/audio/log file |
| GET | `/api/jobs/{id}/stream` | **SSE** — `event: event` lines, plus `meta`(replay_done) + `ping` |
| POST | `/api/run` `{date?}` | starts a live SIMULATION job → `{job_id,status}` |
| POST | `/api/jobs/{id}/rerun/{node_id}` | deterministic = completed; external = `requires_conductor` |
| POST | `/api/jobs/{id}/rerun-from/{node_id}` | `{chain:[…]}` |
| POST | `/api/jobs/{id}/regenerate-images` | `requires_conductor` (research untouched) |
| POST | `/api/jobs/{id}/rewrite-caption` | completed (images untouched) |
| POST | `/api/jobs/{id}/recheck-quality` | completed (content untouched) |
| POST | `/api/jobs/{id}/approve` · `/reject` | approval state |
| POST | `/api/jobs/{id}/publish` | `requires_conductor` (or 409 with `problems[]`) |
| GET/POST | `/api/settings` | full settings object |

### Node object shape
```ts
type Node = {
  node_id: string; node_name: string;
  component_class: "A"|"B"|"C"|"Cprime"|"D"|"E"|"F"|"G";
  component_type: string;      // "LLM Agent" | "Python Module" | "MCP Service" | …
  intelligent: boolean;        // true only for Market Sentinel + Claude Conductor
  actual_component: string;    // real file/service
  external: boolean;           // purple node
  in_graph: boolean;           // story_studio is false
  role: string; status: string; ord: number;
  started_at, completed_at, duration_ms, retry_count, progress,
  input_artifact, output_artifact, summary, error;
};
```
### Event shape (SSE + /events)
`{event_id, seq, job_id, node_id, node_name, actual_component, component_class,
component_type, intelligent, event_type, status, message, progress, payload,
artifact_refs, timestamp}`. Event types: `job.*`, `node.started|progress|log|
artifact_created|completed|failed|retrying|blocked`, `quality.started|passed|
failed`, `approval.required|received`, `publish.started|progress|completed|failed`.

## The 16 graph nodes (order) + the side node
`closing_bell → claude_conductor → market_sentinel → conviction_gate →
slide_architect → art_director → prompt_forge → nano_studio → pixel_lab →
caption_desk → hashtag_desk → compliance_shield → meta_auditor → publish_gate →
ig_courier → run_vault`, plus **story_studio** (side branch, `in_graph:false`).

## Status → colour
`waiting`=slate · `running`/`progress`=teal · `completed`=green · `published`=green-glow ·
`failed`=red · `retrying`=amber · `blocked`/`approval_required`=blue · `pending`=purple ·
`skipped`=muted. **External nodes (nano_studio, ig_courier) = purple accent.**

## Design tokens (premium dark finance newsroom)
- bg `#05070A`; cards `#0B1117`/`#0E1621`; borders `rgba(148,163,184,.12)`.
- accents: teal `#1FB6A6`/cyan `#22D3EE`; success `#27C281`; warn `#F2994A`;
  error `#EF4444`; external/MCP purple `#8B5CF6`; text white/`#94A3B8`.
- Sans (Inter/Geist) for UI; **mono (JetBrains/Geist Mono) for logs + JSON only**.
- Glass cards (subtle border + faint inner glow), generous spacing, thin rules,
  soft glow on the active node, calm motion (Framer) — no neon, no cyberpunk.

## Pages (→ endpoints)
1. `/dashboard` — `/api/meta`, `/api/jobs` (latest). Cards: Current Run, Market
   Status, Active Node, Stories Found/Selected, Images Generated, Content/Design/
   Compliance scores, IG Publish status + permalink. Buttons: Run Closing Bell
   (`POST /api/run`), Open Latest Run.
2. `/run/[jobId]` — left node list, center **React Flow** graph (live via SSE),
   right **Node Inspector** (tabs: Overview/Live Logs/Input/Output/Artifacts/
   Errors/Replay), bottom **Live Console** (event stream).
3. `/research/[jobId]` — `01_research.json`: market summary, top-3 story cards,
   data_confidence_note, source table, rejected/threshold info.
4. `/creative/[jobId]` — `03_creative_direction.json` (selected + alternatives),
   `04_images.json` (prompts + negative + finals), 3 slide previews
   (`/artifact/slide_N.jpg`), regenerate buttons.
5. `/review/[jobId]` — 3 finals + `05_caption.json` + `06_hashtags.json` +
   score cards (content/design/compliance/aesthetic) + approve/reject/hold.
6. `/publish/[jobId]` — publish checklist + console; show permalink only if the
   job actually has `instagram_post_url`.
7. `/archive` — `/api/jobs` table with thumbnails/scores/status/permalink.
8. `/settings` — `/api/settings` GET/POST (schedule 5 PM IST, thresholds,
   integrations status, brand, output folder, db path).

## Components
AppShell, Sidebar, TopBar, StatusBadge, ScoreCard, NodeTimeline, PipelineGraph,
PipelineNode, NodeInspector, LiveConsole, JsonViewer, ArtifactPreview,
ImageCarouselPreview, CreativeDirectionCard, PromptViewer, PublishChecklist,
RunArchiveTable, ClassBadge (A–G).

## Honesty rules (non-negotiable in UI)
- Show each node's real `component_type` + `intelligent` flag. Only Market
  Sentinel and Claude Conductor are intelligent.
- Never render "Published" unless the job has a real `instagram_post_url`.
- Surface `requires_conductor` responses as **"Requires Claude Code conductor"**
  (not an error, not a fake success).
- Empty/missing data → clean empty states, never crash.

## Build order
scaffold + tokens → lib/api.ts + lib/sse.ts + lib/types.ts + constants →
AppShell/Sidebar/TopBar → Dashboard → Run page (graph+inspector+console+SSE) →
Research → Creative → Review → Publish → Archive → Settings → polish → QA.
