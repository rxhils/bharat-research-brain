"""Native Photo Reel Slides framework.

Produces 5 individual 1080x1920 image slides for Instagram's NATIVE photo
Reel flow (create Reel -> Select Multiple -> add Instagram music -> post).
This is NOT a carousel and NOT the legacy AI-video reel pipeline.

Default publish mode is `native_photo_reel_manual` (user uploads the images
manually in Instagram). `slideshow_video_reel_auto` (images -> MP4 -> API
publish) exists only as an explicit opt-in for automated publishing.

Fully separate from maven_instagram (carousel — never touched) and from the
legacy maven_reels.pipeline video framework (read-only imports at most).
"""
