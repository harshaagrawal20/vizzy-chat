from __future__ import annotations

import json
import os
import shutil
import urllib.request
import zipfile
from pathlib import Path
from textwrap import shorten

from app.services.generator import generate_assets, detect_task_type, TaskType


BASE_DIR = Path(__file__).resolve().parent.parent.parent
GENERATED_DIR = BASE_DIR / "generated"
EXPORTS_DIR   = BASE_DIR / "exports"


# ── Anthropic API helper ──────────────────────────────────────────────────────
# Used for model-generated copy and story outlines.
# Falls back to templates if the key is absent or the call fails.

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL   = "claude-sonnet-4-20250514"


def _call_claude(system: str, user: str, max_tokens: int = 400) -> str | None:
    """
    Call the Anthropic Messages API and return the text content.
    Returns None on any failure so the caller can fall back to templates.
    """
    if not ANTHROPIC_API_KEY:
        return None
    try:
        payload = json.dumps({
            "model":      ANTHROPIC_MODEL,
            "max_tokens": max_tokens,
            "system":     system,
            "messages":   [{"role": "user", "content": user}],
        }).encode("utf-8")
        request = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=payload,
            headers={
                "Content-Type":      "application/json",
                "x-api-key":         ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
        return data["content"][0]["text"].strip()
    except Exception:
        return None


# ── Copy generation (model-generated, template fallback) ─────────────────────

def _generate_copy_model(mode: str, prompt: str, brand_context: dict | None) -> str:
    brand_hint = ""
    if brand_context:
        parts = []
        if brand_context.get("business_name"):
            parts.append(f"Business: {brand_context['business_name']}")
        if brand_context.get("brand_voice"):
            parts.append(f"Brand voice: {brand_context['brand_voice']}")
        if brand_context.get("tagline"):
            parts.append(f"Tagline: {brand_context['tagline']}")
        if brand_context.get("values_keywords"):
            parts.append(f"Values: {', '.join(brand_context['values_keywords'][:4])}")
        brand_hint = "\n".join(parts)

    if mode == "business":
        system = (
            "You are a senior brand copywriter. Write concise, premium marketing copy "
            "for a business visual campaign. Output exactly three lines:\n"
            "Headline: (punchy, 8 words max)\n"
            "Support: (one supporting sentence for signage or social)\n"
            "CTA: (3–5 word call to action)\n"
            "No preamble. No markdown. Just the three lines."
        )
        user = f"Creative brief: {prompt}\n{brand_hint}"
    else:
        system = (
            "You are a warm, creative copywriter for personal art and home décor. "
            "Write copy for a personal visual. Output exactly three lines:\n"
            "Caption: (reflective, personal, 12 words max)\n"
            "Poster line: (short enough for print, emotionally resonant)\n"
            "Affirmation: (one uplifting sentence)\n"
            "No preamble. No markdown. Just the three lines."
        )
        user = f"Creative prompt: {prompt}"

    result = _call_claude(system, user, max_tokens=200)
    return result if result else _copy_template(mode, prompt)


def _copy_template(mode: str, prompt: str) -> str:
    """Original template fallback."""
    if mode == "business":
        return (
            "Headline: Elevated, inviting, and premium without sounding expensive.\n"
            "Support copy: Designed for signage, social captions, and frame messaging.\n"
            f"Campaign focus: {shorten(prompt, width=96, placeholder='...')}"
        )
    return (
        "Caption: A reflective visual direction with a more personal emotional tone.\n"
        "Poster line: Short enough for print, warm enough for a lived-in space.\n"
        f"Prompt essence: {shorten(prompt, width=96, placeholder='...')}"
    )


# ── Story generation (model-generated, template fallback) ─────────────────────

def _generate_story_model(prompt: str) -> str:
    system = (
        "You are a children's picture book author. Given a creative prompt, write a "
        "3-scene story outline for a visual storybook. Each scene is one sentence: "
        "vivid, imaginative, child-appropriate. Format:\n"
        "Scene 1: ...\nScene 2: ...\nScene 3: ...\n"
        "Then add one line: Visual cue: (a single phrase describing the visual mood)\n"
        "No preamble. No markdown beyond the scene labels."
    )
    result = _call_claude(system, prompt, max_tokens=250)
    return result if result else _story_template(prompt)


def _story_template(prompt: str) -> str:
    return (
        "Scene 1: Set the mood and introduce the emotional or visual world.\n"
        "Scene 2: Bring the main subject into focus with a stronger narrative beat.\n"
        "Scene 3: End with a memorable frame that feels display-ready or shareable.\n"
        f"Creative cue: {shorten(prompt, width=96, placeholder='...')}"
    )


# ── Deploy / export helpers ───────────────────────────────────────────────────

def ensure_exports_dir() -> None:
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)


def _export_zip(asset_filenames: list[str], conversation_id: int | None) -> dict:
    """Bundle all generated assets into a ZIP file for download."""
    ensure_exports_dir()
    zip_name = f"vizzy-export-{conversation_id or 'chat'}.zip"
    zip_path = EXPORTS_DIR / zip_name

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for fname in asset_filenames:
            src = GENERATED_DIR / fname
            if src.exists():
                zf.write(src, arcname=fname)

    return {
        "surface": "zip",
        "file_path": str(zip_path),
        "download_url": f"/exports/{zip_name}",
        "label": "Download ZIP",
    }


def _export_surface(
    asset_filenames: list[str],
    surface: str,
    conversation_id: int | None,
) -> dict:
    """
    Concrete export for a named surface.

    frame / print  → copies PNGs to exports dir, returns download URL
    social         → copies with social-crop label (stub: actual resize TODO)
    email          → stub returns instructions (real: HTML email builder TODO)
    zip            → full bundle
    """
    ensure_exports_dir()

    if surface == "zip":
        return _export_zip(asset_filenames, conversation_id)

    if surface in ("frame", "print", "social"):
        exported = []
        for fname in asset_filenames:
            src = GENERATED_DIR / fname
            if not src.exists():
                continue
            dest_name = f"{surface}-{fname}"
            dest = EXPORTS_DIR / dest_name
            shutil.copy2(src, dest)
            exported.append(f"/exports/{dest_name}")
        return {
            "surface": surface,
            "download_urls": exported,
            "label": f"Download for {surface.title()}",
            # Social hook: plug in your sharing API key here
            "social_stub": (
                {
                    "note": "Social publishing stub. Wire INSTAGRAM_TOKEN / META_API_KEY to push directly.",
                    "suggested_caption_prompt": "Generate a short social caption for this visual.",
                }
                if surface == "social"
                else None
            ),
        }

    if surface == "email":
        # Email stub: returns a template the user can paste into their ESP
        return {
            "surface": "email",
            "stub": True,
            "note": "Email publishing stub. Wire SENDGRID_API_KEY / MAILCHIMP_API_KEY to send directly.",
            "html_template_hint": (
                "<table><tr><td>"
                + "".join(f'<img src="REPLACE_WITH_CDN_URL/{f}" width="600"/>' for f in asset_filenames)
                + "</td></tr></table>"
            ),
        }

    return {"surface": surface, "error": "Unknown surface"}


def _deploy_card(
    mode: str,
    asset_filenames: list[str],
    conversation_id: int | None,
) -> dict:
    """Build the Deploy asset card with real download actions."""
    if mode == "business":
        surface_text = (
            "Surfaces: frame, email, social, print signage.\n"
            "Use the action buttons below to download files for each surface, "
            "or grab the full ZIP bundle. Social and email publishing can be wired "
            "to your preferred platform once API keys are configured."
        )
        actions = [
            {"label": "Frame version",  "prompt_suffix": "Prepare this concept for a frame-friendly version with cleaner composition."},
            {"label": "Social version", "prompt_suffix": "Adapt this concept for a social-ready crop and caption approach."},
            {"label": "Download ZIP",   "action": "export_zip"},
            {"label": "Print version",  "action": "export_print"},
            {"label": "Email version",  "action": "export_email"},
        ]
    else:
        surface_text = (
            "Surfaces: frame display, poster print, saved style set, personal sharing.\n"
            "Download your visuals below as PNG files or as a ZIP bundle."
        )
        actions = [
            {"label": "Frame version",  "prompt_suffix": "Prepare this concept for a frame-friendly version with cleaner composition."},
            {"label": "Download ZIP",   "action": "export_zip"},
            {"label": "Save style",     "prompt_suffix": "Remember this style and apply it more strongly to future generations."},
        ]

    return {
        "type": "Deploy",
        "title": "Surface Plan",
        "description": "Export and deploy your visuals across the surfaces that matter to you.",
        "text_content": surface_text,
        "asset_filenames": asset_filenames,
        "conversation_id": conversation_id,
        "actions": actions,
    }


# ── Title suggestion ──────────────────────────────────────────────────────────

def suggest_title(prompt: str, mode: str) -> str:
    prefix = "Home" if mode == "home" else "Business"
    return f"{prefix}: {shorten(prompt, width=36, placeholder='...')}"


# ── Main reply builder ────────────────────────────────────────────────────────

def build_assistant_reply(
    prompt: str,
    mode: str,
    memory_keywords: list[str] | None = None,
    attachments: list[dict] | None = None,
    brand_context: dict | None = None,
    conversation_id: int | None = None,
) -> tuple[str, str, list[dict]]:
    lowered = prompt.lower()
    memory_keywords = memory_keywords or []
    attachments     = attachments or []

    task_type = detect_task_type(prompt, attachments)

    # ── Generate visual assets ────────────────────────────────────────────────
    assets = generate_assets(
        prompt=prompt,
        mode=mode,
        count=3,
        memory_keywords=memory_keywords,
        attachments=attachments,
        brand_context=brand_context,
    )

    # Collect filenames for export bundling
    asset_filenames = [a.get("filename", "") for a in assets if a.get("filename")]

    # ── Story or Copy card ────────────────────────────────────────────────────
    if task_type == TaskType.STORY or "story" in lowered or "kids" in lowered:
        story_text = _generate_story_model(prompt)
        assets.append({
            "type": "Story Outline",
            "title": "Narrative Sequence",
            "description": "A model-generated scene-by-scene story scaffold to pair with the visuals.",
            "text_content": story_text,
            "actions": [
                {"label": "Extend story",  "prompt_suffix": "Expand this into a longer illustrated storybook narrative."},
                {"label": "Add scene",     "prompt_suffix": "Add one more scene to this sequence with stronger emotional detail."},
                {"label": "Download ZIP",  "action": "export_zip"},
            ],
        })
    else:
        copy_text = _generate_copy_model(mode, prompt, brand_context)
        assets.append({
            "type": "Copy",
            "title": "Messaging Layer",
            "description": "Model-generated copy and poster-ready language from the same creative brief.",
            "text_content": copy_text,
            "actions": [
                {"label": "Shorter copy", "prompt_suffix": "Rewrite this with shorter, sharper messaging."},
                {"label": "Warmer tone",  "prompt_suffix": "Keep this concept but make the messaging warmer and more human."},
                {"label": "Brand copy",   "prompt_suffix": "Rewrite this copy to more strongly reflect the brand voice and values."},
            ],
        })

    # ── Video card (when task is video) ───────────────────────────────────────
    if task_type == TaskType.VIDEO:
        assets.append({
            "type": "Video",
            "title": "Motion Concept",
            "description": (
                "Video generation is in the roadmap. The motion board above represents "
                "the visual concept. Wire a video backend (Replicate, RunwayML, etc.) "
                "in generator.py → SUPPORTED_VIDEO_BACKENDS to activate real synthesis."
            ),
            "text_content": (
                "Planned pipeline: AnimateDiff / Stable Video Diffusion / RunwayML\n"
                "Status: Backend not yet configured — concept board generated instead.\n"
                "To activate: add your video API key and update SUPPORTED_VIDEO_BACKENDS."
            ),
            "actions": [
                {"label": "Refine concept", "prompt_suffix": "Refine the motion concept with more specific movement and mood direction."},
                {"label": "Still version",  "prompt_suffix": "Generate a high-quality still version of this motion concept."},
            ],
        })

    # ── Deploy card ───────────────────────────────────────────────────────────
    assets.append(_deploy_card(mode, asset_filenames, conversation_id))

    # ── Reply text ────────────────────────────────────────────────────────────
    if mode == "home":
        tag = "Generated response"
        if task_type == TaskType.IMAGE_TO_IMAGE:
            text = (
                "I used your uploaded reference to create transformed visual directions. "
                "The img2img pipeline reinterprets your image in the requested style, "
                "with narrative and deploy-ready layers for further refinement."
            )
        elif task_type == TaskType.VIDEO:
            text = (
                "I detected a motion/video request and generated a concept board. "
                "When a video backend is configured, this will produce real animated output. "
                "Use the motion concept to refine the visual direction first."
            )
        elif task_type == TaskType.STORY:
            text = (
                "I interpreted this as a story request and created visual scenes with "
                "a model-generated narrative outline you can refine scene by scene."
            )
        elif "quote" in lowered or "poster" in lowered:
            text = (
                "I created several visual directions for your poster, with matching "
                "copy and a download plan so you can take it straight to print or frame."
            )
        else:
            text = (
                "I turned your prompt into personal creative directions — visual, "
                "narrative, and deploy-ready — so you can refine what resonates."
            )
    else:
        tag = "Asset response"
        if task_type == TaskType.IMAGE_TO_IMAGE:
            text = (
                "I used your uploaded product or reference image to generate campaign-style "
                "transformations, with brand-aware copy and surface planning for reuse."
            )
        elif task_type == TaskType.VIDEO:
            text = (
                "I detected a video/loop request and generated a motion concept board. "
                "Wire a video backend to activate real clip synthesis. "
                "Brand copy and surface planning are ready for when the video is live."
            )
        elif "poster" in lowered or "signage" in lowered:
            text = (
                "I treated this as a signage brief and created reusable visual variants "
                "with brand-aligned copy and surface planning across frame, social, and print."
            )
        else:
            text = (
                "I interpreted this as a brand-facing brief and created visual outputs, "
                "model-generated messaging, and deployment directions for multiple surfaces."
            )

    return tag, text, assets


# ── Export endpoint handler ───────────────────────────────────────────────────
# Called directly from main.py's export API route.

def handle_export(
    surface: str,
    asset_filenames: list[str],
    conversation_id: int | None = None,
) -> dict:
    return _export_surface(asset_filenames, surface, conversation_id)