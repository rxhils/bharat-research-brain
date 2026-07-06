"""Agent 6 — Native Photo Reel Exporter.

Packages the 5 individual images for MANUAL Instagram Reel upload
(create Reel -> Select Multiple). Produces: 5 cleanly named PNGs, one ZIP,
a cover image, and the exact manual upload steps. Never publishes anything.
"""
from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

from . import config, state


def run(job_id: str) -> dict:
    design = state.load_artifact(job_id, "slide_design") or {}
    images = sorted(design.get("generated_images", []),
                    key=lambda i: i.get("slide_number", 0))
    missing = [i["slide_number"] for i in images if not Path(i["path"]).exists()]
    if len(images) != config.SLIDE_COUNT or missing:
        payload = {"mode": "native_photo_reel_manual", "image_paths": [],
                   "zip_path": "", "cover_image": "",
                   "instagram_manual_steps": config.INSTAGRAM_MANUAL_STEPS,
                   "recommended_order": [], "status": "blocked",
                   "note": f"need {config.SLIDE_COUNT} rendered slides "
                           f"(missing: {missing or 'all'})",
                   "generated_at": config.now_ist().isoformat(timespec="seconds")}
        state.save_artifact(job_id, "export", payload)
        return payload

    edir = state.export_dir(job_id)
    out_paths: list[str] = []
    for img in images:
        n = img["slide_number"]
        dest = edir / f"maven_photo_reel_{job_id}_slide_{n}.png"
        shutil.copyfile(img["path"], dest)
        out_paths.append(str(dest))

    cover = edir / f"maven_photo_reel_{job_id}_cover.png"
    shutil.copyfile(images[0]["path"], cover)

    zip_path = edir / f"maven_photo_reel_{job_id}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in out_paths:
            zf.write(p, Path(p).name)
        zf.write(cover, cover.name)
        script = state.load_artifact(job_id, "slide_script") or {}
        zf.writestr("caption.txt",
                    (script.get("caption", "") + "\n\n"
                     + " ".join(script.get("hashtags", []))))
        zf.writestr("upload_steps.txt",
                    "\n".join(f"{i}. {s}" for i, s in
                              enumerate(config.INSTAGRAM_MANUAL_STEPS, 1)))

    payload = {
        "mode": "native_photo_reel_manual",
        "image_paths": out_paths,
        "zip_path": str(zip_path),
        "cover_image": str(cover),
        "instagram_manual_steps": config.INSTAGRAM_MANUAL_STEPS,
        "recommended_order": [1, 2, 3, 4, 5],
        "status": "exported",
        "generated_at": config.now_ist().isoformat(timespec="seconds"),
    }
    state.save_artifact(job_id, "export", payload)
    return payload
