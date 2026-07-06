"""Agent — Higgsfield Production Agent (full-stack executor).

Executes the Blueprint + Production Routing + Production Prompts:
  footage scenes  -> Higgsfield video models (real) / ffmpeg placeholder (sim)
  card scenes     -> nano_banana_pro designed still (real, CLI transport) then a
                     gentle local zoom turns it into a clip (local motion only —
                     the DESIGN is Higgsfield's); matplotlib placeholder in sim
Local code never designs production text; simulation placeholders are clearly
marked. Real mode is UI-confirmation-gated (REQUIRE_CREDIT_CONFIRMATION) and
never runs from Claude Code (ALLOW_PRODUCTION_FROM_CLAUDE=false).
Writes clips to higgsfield_clips/ (so inspector/assembler flow is unchanged),
records via scene_generator.record_results, and writes 34_production_result.json.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from . import config, state, step_higgsfield_scene_generator as sg


def _ffmpeg() -> str:
    exe = shutil.which("ffmpeg")
    if not exe:
        raise RuntimeError("ffmpeg required")
    return exe


def _card_to_clip(ff: str, img: Path, dest: Path, seconds: float) -> None:
    """Higgsfield-designed card still -> clip. STATIC hold (no zoom/push-in) —
    the designed card is shown exactly as generated, no local motion."""
    subprocess.run(
        [ff, "-y", "-loop", "1", "-i", str(img),
         "-vf", ("scale=1080:1920:force_original_aspect_ratio=increase,"
                 "crop=1080:1920,setsar=1,fps=30"),
         "-t", f"{seconds:.2f}", "-c:v", "libx264", "-preset", "veryfast",
         "-pix_fmt", "yuv420p", str(dest)], check=True, capture_output=True, timeout=180)


def _sim_card(img: Path, text: str) -> None:
    """SIMULATION-ONLY placeholder card (clearly not production design)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig = plt.figure(figsize=(6.75, 12), dpi=160)
    fig.patch.set_facecolor("#0A1220")
    ax = fig.add_axes([0, 0, 1, 1]); ax.axis("off"); ax.set_facecolor("#0A1220")
    ax.text(0.5, 0.52, text or "CARD", ha="center", va="center", color="#F8FAFC",
            fontsize=30, fontweight="bold", wrap=True)
    ax.text(0.5, 0.06, "SIMULATION PREVIEW", ha="center", color="#2FE6A6", fontsize=10)
    fig.savefig(img, facecolor=fig.get_facecolor()); plt.close(fig)


def run(date: str, *, simulate: bool | None = None, approved_from_ui: bool = False) -> dict:
    from . import higgsfield_client as hf  # noqa: PLC0415

    blueprint = state.load_artifact(date, "higgsfield_blueprint")
    prompts = {p["scene_id"]: p for p in
               state.load_artifact(date, "production_prompts")["prompts"]}
    rd = config.run_dir(date)
    clips_dir = rd / "higgsfield_clips"; clips_dir.mkdir(parents=True, exist_ok=True)
    ff = _ffmpeg()

    use_real = (hf.available() if simulate is None else (not simulate))
    if use_real and config.REQUIRE_CREDIT_CONFIRMATION and not approved_from_ui:
        payload = {"date": date, "mode": "blocked", "approved_by_user": False,
                   "errors": ["real production requires localhost-UI confirmation"],
                   "credits_spent": "not_run"}
        state.save_artifact(date, "production_result", payload)
        return payload

    results, cards, errors = [], [], []
    for s in blueprint["scenes"]:
        sid, dur = s["scene_id"], float(s["duration"])
        p = prompts.get(sid, {})
        dest = clips_dir / f"{sid}.mp4"
        entry = {"shot_id": sid, "clip_path": f"higgsfield_clips/{sid}.mp4",
                 "duration": dur, "model_used": p.get("model_or_tool"),
                 "scene_type": s["scene_type"], "retries": 0}
        try:
            if s.get("requires_text_fidelity"):
                img = clips_dir / f"{sid}_card.png"
                if use_real:
                    hf.generate_image_to_file(p["prompt"], img)
                else:
                    _sim_card(img, s.get("exact_text", ""))
                _card_to_clip(ff, img, dest, dur)
                cards.append({"scene_id": sid, "image": str(img),
                              "exact_text": s.get("exact_text", "")})
            elif use_real:
                hf.generate_video_to_file(p["prompt"], dest,
                                          model=p.get("model_or_tool") or "seedance1_5",
                                          duration=max(4, int(dur)))
            else:
                hf.simulate_video_to_file(dest, purpose=s["purpose"], duration=dur,
                                          seed=abs(hash(sid)) % 99999)
            entry.update(status="completed",
                         cost_credits=0.0 if not use_real else None,
                         mode="real" if use_real else "simulation")
        except Exception as exc:
            entry.update(status="failed", failure_reason=str(exc)[:180])
            errors.append(f"{sid}: {str(exc)[:120]}")
        results.append(entry)

    sg.record_results(date, results)
    payload = {"date": date, "mode": "production" if use_real else "simulation",
               "approved_by_user": approved_from_ui,
               "clips": [r for r in results if r["scene_type"] == "realistic_broll"],
               "text_cards": cards,
               "popup_cards": [c for c in cards if "shot_03" in c["scene_id"]],
               "captions": [], "montage_result": {"engine": "local_stitch_only"},
               "errors": errors,
               "credits_spent": "unknown" if use_real else 0}
    state.save_artifact(date, "production_result", payload)
    return payload
