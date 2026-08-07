from __future__ import annotations

import base64
import hashlib
import html
import io
import json
import random
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from textwrap import shorten

from app.settings import settings


BASE_DIR = Path(__file__).resolve().parent.parent.parent
GENERATED_DIR = BASE_DIR / "generated"

PALETTES = [
    ("#35140f", "#bb4f2b", "#f0b56e", "#fff2da"),
    ("#102542", "#1f5f8b", "#8cc8ff", "#ecf8ff"),
    ("#17341f", "#3a7d44", "#a1d99b", "#f3fff3"),
    ("#421322", "#8c2f5f", "#f4b6d2", "#fff2f8"),
    ("#332038", "#6a4c93", "#f2a6ff", "#faf0ff"),
]

HOME_VARIATIONS = [
    "dreamlike painterly atmosphere, layered emotion, poetic lighting",
    "symbolic interior landscape, intimate tones, gallery composition",
    "surreal memory collage, soft focus, cinematic color harmony",
]

BUSINESS_VARIATIONS = [
    "premium commercial composition, polished lighting, luxury without excess",
    "editorial product framing, refined textures, upscale brand mood",
    "campaign-ready visual, clean merchandising cues, elevated clarity",
]


# ── Task-type detection ───────────────────────────────────────────────────────
# Used by the orchestration layer to route to the right pipeline.

class TaskType:
    TEXT_TO_IMAGE   = "text_to_image"
    IMAGE_TO_IMAGE  = "image_to_image"   # reference image present → img2img
    INPAINTING      = "inpainting"        # mask + reference (future)
    VIDEO           = "video"             # motion/loop requests
    POSTER          = "poster"            # quote / signage with strong text
    STORY           = "story"             # kids / narrative sequences


def detect_task_type(prompt: str, attachments: list[dict]) -> str:
    """
    Classify a request into a TaskType so we can route to the right backend.
    Priority: explicit attachments beat keyword heuristics.
    """
    lowered = prompt.lower()
    has_image = bool(attachments)

    if "video" in lowered or "loop" in lowered or "animate" in lowered or "motion" in lowered:
        return TaskType.VIDEO
    if has_image:
        return TaskType.IMAGE_TO_IMAGE
    if "story" in lowered or "kids" in lowered or "storybook" in lowered:
        return TaskType.STORY
    if "poster" in lowered or "quote" in lowered or "signage" in lowered:
        return TaskType.POSTER
    return TaskType.TEXT_TO_IMAGE


# ── Helpers ───────────────────────────────────────────────────────────────────

def ensure_generated_dir() -> None:
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)


def _seed_for(prompt: str, variant: int) -> int:
    digest = hashlib.sha256(f"{prompt}:{variant}".encode("utf-8")).hexdigest()
    return int(digest[:16], 16)


def _variant_prompt(prompt: str, mode: str, variant: int) -> str:
    variations = HOME_VARIATIONS if mode == "home" else BUSINESS_VARIATIONS
    return variations[variant % len(variations)]


def _asset_type(prompt: str, mode: str, index: int) -> str:
    lowered = prompt.lower()
    if "story" in lowered or "kids" in lowered:
        return "Story Scene"
    if "poster" in lowered or "quote" in lowered or "signage" in lowered:
        return "Poster"
    if "video" in lowered or "loop" in lowered:
        return "Motion Board"
    if mode == "business" and index == 1:
        return "Campaign Visual"
    return "Artwork"


def _asset_title(mode: str, asset_type: str, index: int) -> str:
    if mode == "home":
        options = ["Dream Draft", "Memory Echo", "Inner Atlas"]
    else:
        options = ["Hero Concept", "Retail Variant", "Campaign Echo"]
    return f"{options[index % len(options)]} {asset_type}"


def _asset_description(
    mode: str, prompt: str, backend: str,
    memory_keywords: list[str], has_attachments: bool,
    variant: int, task_type: str,
) -> str:
    prefix = (
        "Built to feel personal, symbolic, and open to refinement."
        if mode == "home"
        else "Built to feel branded, reusable, and deployable across surfaces."
    )
    suffix = shorten(prompt, width=68, placeholder="...")
    memory_hint = f" Learned taste: {', '.join(memory_keywords[:3])}." if memory_keywords else ""
    attachment_hint = " Reference image used for transformation." if has_attachments else ""
    task_hint = f" Task: {task_type.replace('_', ' ')}."
    variation_hint = _variant_prompt(prompt, mode, variant)
    return (
        f"{prefix} Render backend: {backend}.{attachment_hint}{memory_hint}"
        f"{task_hint} Variation focus: {variation_hint}. Prompt: {suffix}"
    )


def _asset_actions(mode: str, asset_type: str) -> list[dict]:
    common = [
        {"label": "Refine", "prompt_suffix": f"Keep this {asset_type.lower()} direction but refine the details and composition."},
        {"label": "Generate more", "prompt_suffix": f"Create more variations in this {asset_type.lower()} direction with stronger contrast from previous outputs."},
        {"label": "Download", "action": "download"},
    ]
    if mode == "home":
        common.append({"label": "Save style", "prompt_suffix": "Remember this style and apply it more strongly to future generations."})
        common.append({"label": "❤ Favourite", "action": "favourite"})
    else:
        common.append({"label": "Use on frame", "prompt_suffix": "Adapt this concept to be more suitable for frame display and signage."})
        common.append({"label": "Add to campaign", "action": "add_to_campaign"})
    return common


def _slug(prompt: str) -> str:
    return hashlib.sha1(prompt.encode("utf-8")).hexdigest()[:10]


def _compose_prompt(
    prompt: str, mode: str,
    memory_keywords: list[str], attachments: list[dict],
    variant: int, brand_context: dict | None = None,
) -> str:
    parts = [prompt]
    if memory_keywords:
        parts.append(f"Preferred style cues: {', '.join(memory_keywords[:4])}")
    if attachments:
        parts.append("Transform and reinterpret the uploaded reference image in the new style described.")
    parts.append(f"Variation intent: {_variant_prompt(prompt, mode, variant)}")

    if mode == "business" and brand_context:
        if brand_context.get("brand_voice"):
            parts.append(f"Brand voice: {brand_context['brand_voice']}")
        if brand_context.get("values_keywords"):
            parts.append(f"Brand values: {', '.join(brand_context['values_keywords'][:4])}")
        if brand_context.get("business_type"):
            parts.append(f"Business type: {brand_context['business_type']}")
        parts.append("premium commercial visual, usable across signage, frame, social, and campaign surfaces")
    else:
        parts.append("personal artistic expression, emotionally resonant, gallery-worthy")

    return ", ".join(parts)


def _model_specific_parameters(variant: int) -> dict:
    model = settings.hf_model.lower()
    seed = random.randint(1, 2**31 - 1) if "flux.1-schnell" in model else _seed_for(settings.hf_model, variant)
    if "flux.1-schnell" in model:
        return {
            "guidance_scale": 3.5,
            "num_inference_steps": min(settings.image_steps, 4),
            "width": settings.image_width,
            "height": settings.image_height,
            "seed": seed,
        }
    return {
        "guidance_scale": 7,
        "num_inference_steps": settings.image_steps,
        "width": settings.image_width,
        "height": settings.image_height,
        "negative_prompt": "blurry, distorted, deformed, watermark, text",
        "seed": seed,
    }


GROQ_SVG_URL   = "https://api.groq.com/openai/v1/chat/completions"
GROQ_SVG_MODEL = "llama-3.3-70b-versatile"  # higher TPM limit than 8b-instant

_SVG_BATCH_SYSTEM = """You are a world-class SVG visual artist creating cinematic, gallery-quality artwork. Generate 3 DISTINCT, breathtaking SVG illustrations of the same scene.

STRICT OUTPUT FORMAT — output ONLY this, zero other text:
===SVG1===
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024" width="1024" height="1024">
...rich svg content...
</svg>
===SVG2===
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024" width="1024" height="1024">
...different mood and palette...
</svg>
===SVG3===
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024" width="1024" height="1024">
...third distinct interpretation...
</svg>

MANDATORY ARTISTIC REQUIREMENTS for EACH SVG:
1. ATMOSPHERE: Use <defs> with at least 3 layered radialGradient or linearGradient fills for sky, ground, and accent lighting
2. DEPTH: Add <filter> with feGaussianBlur for background blur (stdDeviation 4-8), creating depth-of-field
3. LAYERS: Build minimum 4 depth layers — distant background, mid-background, midground, foreground
4. DETAIL: Include at minimum 40 SVG elements (rects, circles, paths, ellipses, polygons)
5. ORGANIC SHAPES: Use complex <path d="M...C...S...Q..."> bezier curves for natural forms (clouds, terrain, foliage, waves)
6. LIGHTING: Add atmospheric glow using radialGradient with high opacity center fading to transparent
7. TEXTURE: Layer semi-transparent overlapping shapes (opacity 0.1-0.4) for texture and richness
8. COLOR HARMONY: Each SVG uses a distinct cinematic color palette (e.g. golden hour, moonlit blue, mystical purple)
9. SILHOUETTES: Use dark foreground silhouette shapes against lighter background for dramatic contrast
10. NO BASIC SHAPES ALONE: Never just place a plain circle for sun or rectangle for sky — always use gradients and multiple layered elements

Each SVG must look like a premium, painterly illustration — NOT clip art. Think: Studio Ghibli backgrounds, atmospheric landscape paintings, cinematic concept art.
No markdown fences. No explanation. Only the SVG blocks."""

# Cache: (prompt, mode) → list of SVG strings from the batch call
_svg_batch_cache: dict[tuple[str, str], list[str]] = {}


def _fetch_ai_svg_batch(prompt: str, mode: str, count: int, memory_keywords: list[str]) -> list[str]:
    """Single Groq call → list of `count` SVG strings."""
    from app.settings import settings as _s
    if not _s.groq_api_key:
        raise ValueError("No GROQ_API_KEY")

    style_hint = ", ".join(memory_keywords[:3]) if memory_keywords else "cinematic, vibrant"
    user_msg = (
        f"Create {count} stunning, gallery-quality SVG artworks of this scene: {prompt}. "
        f"Style influences: {style_hint}. "
        f"Each must be a richly layered, atmospheric, cinematic illustration with gradients, blur filters, "
        f"bezier path terrain, organic shapes, and dramatic lighting. "
        f"Use the ===SVG1=== / ===SVG2=== / ===SVG3=== format exactly. "
        f"Make each one visually distinct with a different color mood."
    )

    payload = json.dumps({
        "model":    GROQ_SVG_MODEL,
        "messages": [
            {"role": "system", "content": _SVG_BATCH_SYSTEM},
            {"role": "user",   "content": user_msg},
        ],
        "temperature": 0.9,
        "max_tokens":  8000,
    }).encode("utf-8")

    req = urllib.request.Request(
        GROQ_SVG_URL, data=payload,
        headers={
            "Content-Type":  "application/json",
            "Authorization": f"Bearer {_s.groq_api_key}",
            "User-Agent":    "python-httpx/0.24.0",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        resp = json.loads(r.read().decode("utf-8"))

    raw = resp["choices"][0]["message"]["content"]

    results: list[str] = []
    for i in range(1, count + 1):
        marker      = f"===SVG{i}==="
        next_marker = f"===SVG{i + 1}===" if i < count else None
        start = raw.find(marker)
        if start == -1:
            continue
        start += len(marker)
        end = raw.find(next_marker, start) if next_marker else len(raw)
        chunk = raw[start:end].strip()
        svg_s = chunk.find("<svg")
        svg_e = chunk.rfind("</svg>")
        if svg_s != -1 and svg_e != -1:
            svg_str = chunk[svg_s: svg_e + 6]
            # Ensure xmlns is present — required for <img> tag rendering
            if 'xmlns=' not in svg_str:
                svg_str = svg_str.replace('<svg', '<svg xmlns="http://www.w3.org/2000/svg"', 1)
            results.append(svg_str)

    if not results:
        raise ValueError("No ===SVGn=== markers found in response")
    return results


def _svg_markup(prompt: str, mode: str, variant: int, memory_keywords: list[str]) -> str:
    """Abstract fallback SVG used when Groq is unavailable."""
    seed = _seed_for(prompt, variant)
    randomizer = random.Random(seed)
    colors = PALETTES[seed % len(PALETTES)]
    label = html.escape(shorten(prompt, width=56, placeholder="..."))
    abstract_label = "Emotional composition" if mode == "home" else "Brand composition"
    memory_label = html.escape(", ".join(memory_keywords[:2]) if memory_keywords else "adaptive style")

    circles = []
    for _ in range(9):
        radius = randomizer.randint(80, 240)
        x = randomizer.randint(40, 980)
        y = randomizer.randint(40, 980)
        opacity = randomizer.uniform(0.10, 0.28)
        fill = colors[randomizer.randint(0, len(colors) - 1)]
        circles.append(f'<circle cx="{x}" cy="{y}" r="{radius}" fill="{fill}" opacity="{opacity:.2f}" />')

    lines = []
    for _ in range(8):
        x1 = randomizer.randint(0, 1024)
        y1 = randomizer.randint(0, 1024)
        x2 = randomizer.randint(0, 1024)
        y2 = randomizer.randint(0, 1024)
        stroke = colors[randomizer.randint(0, len(colors) - 1)]
        width = randomizer.randint(2, 7)
        opacity = randomizer.uniform(0.14, 0.34)
        lines.append(
            f'<path d="M {x1} {y1} Q {randomizer.randint(0, 1024)} {randomizer.randint(0, 1024)} {x2} {y2}" '
            f'stroke="{stroke}" stroke-width="{width}" stroke-linecap="round" fill="none" opacity="{opacity:.2f}" />'
        )

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="1024" viewBox="0 0 1024 1024" '
        f'role="img" aria-label="{label}">\n'
        f'  <defs>\n'
        f'    <linearGradient id="grad-{seed}" x1="0%" y1="0%" x2="100%" y2="100%">\n'
        f'      <stop offset="0%" stop-color="{colors[0]}" />\n'
        f'      <stop offset="45%" stop-color="{colors[1]}" />\n'
        f'      <stop offset="100%" stop-color="{colors[2]}" />\n'
        f'    </linearGradient>\n'
        f'    <filter id="blur-{seed}"><feGaussianBlur stdDeviation="12" /></filter>\n'
        f'  </defs>\n'
        f'  <rect width="1024" height="1024" fill="url(#grad-{seed})" />\n'
        f'  <g filter="url(#blur-{seed})">{"".join(circles)}</g>\n'
        f'  <g>{"".join(lines)}</g>\n'
        f'  <rect x="56" y="770" width="520" height="140" rx="28" fill="{colors[3]}" opacity="0.82" />\n'
        f'  <text x="92" y="824" fill="{colors[0]}" font-size="26" font-family="Arial, sans-serif" letter-spacing="4">ATELIERAI</text>\n'
        f'  <text x="92" y="868" fill="{colors[1]}" font-size="30" font-weight="700" font-family="Arial, sans-serif">{abstract_label}</text>\n'
        f'  <text x="92" y="905" fill="{colors[1]}" font-size="18" font-family="Arial, sans-serif">Style cues: {memory_label}</text>\n'
        f'</svg>\n'
    )


def _write_svg(prompt: str, mode: str, index: int, memory_keywords: list[str]) -> tuple[str, str]:
    filename = f"{mode}-{_slug(prompt)}-{index + 1}.svg"
    filepath = GENERATED_DIR / filename

    # On index 0: fire ONE batch Groq call to generate all 3 variants
    cache_key = (prompt, mode)
    if index == 0 and cache_key not in _svg_batch_cache:
        try:
            _svg_batch_cache[cache_key] = _fetch_ai_svg_batch(prompt, mode, 3, memory_keywords)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError,
                KeyError, IndexError, ValueError, OSError):
            _svg_batch_cache[cache_key] = []  # mark failed; use fallback

    cached = _svg_batch_cache.get(cache_key, [])
    if index < len(cached):
        filepath.write_text(cached[index], encoding="utf-8")
        return filename, "groq-svg"

    # Fallback: abstract generative SVG
    filepath.write_text(_svg_markup(prompt, mode, index, memory_keywords), encoding="utf-8")
    return filename, "svg"



# ── HTTP helpers ──────────────────────────────────────────────────────────────

def _request_json(url: str, payload: dict, headers: dict | None = None) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **(headers or {})},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        return json.loads(response.read().decode("utf-8"))


def _request_bytes(url: str, payload: dict | None = None, headers: dict | None = None) -> bytes:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", **(headers or {})},
        method="POST" if payload is not None else "GET",
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        return response.read()


def _save_png_bytes(raw: bytes, prompt: str, mode: str, index: int, source: str) -> tuple[str, str]:
    filename = f"{mode}-{_slug(prompt)}-{index + 1}.png"
    filepath = GENERATED_DIR / filename
    filepath.write_bytes(raw)
    return filename, source


# ── fal.ai backend (FLUX.1-schnell via fal.run — primary recommended backend) ─

FAL_FLUX_URL     = "https://fal.run/fal-ai/flux/schnell"
FAL_IMG2IMG_URL  = "https://fal.run/fal-ai/flux/dev/image-to-image"

_IMAGE_SIZE_MAP = {
    256:  "square",
    512:  "square_hd",
    768:  "square_hd",
    1024: "square_hd",
}


def _fal_image_size() -> str:
    w = settings.image_width
    if w <= 256:
        return "square"
    if w <= 512:
        return "square_hd"
    return "landscape_4_3"


def _generate_fal_txt2img(
    composed_prompt: str, prompt: str, mode: str, index: int,
) -> tuple[str, str]:
    """Generate an image via fal.ai FLUX.1-schnell REST API."""
    if not settings.fal_key:
        raise ValueError("FAL_KEY is not configured")

    payload = json.dumps({
        "prompt":                composed_prompt,
        "num_inference_steps":   min(settings.image_steps, 4),   # schnell max 4
        "guidance_scale":        3.5,
        "image_size":            _fal_image_size(),
        "num_images":            1,
        "enable_safety_checker": False,
        "seed":                  _seed_for(prompt, index),
    }).encode("utf-8")

    req = urllib.request.Request(
        FAL_FLUX_URL,
        data=payload,
        headers={
            "Authorization": f"Key {settings.fal_key}",
            "Content-Type":  "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        resp = json.loads(r.read().decode("utf-8"))

    img_url = resp["images"][0]["url"]
    with urllib.request.urlopen(img_url, timeout=60) as img_r:
        raw = img_r.read()
    return _save_png_bytes(raw, prompt, mode, index, "fal-ai")


def _generate_fal_img2img(
    composed_prompt: str, prompt: str, mode: str, index: int,
    attachments: list[dict],
) -> tuple[str, str]:
    """Image-to-image via fal.ai flux/dev endpoint."""
    if not settings.fal_key:
        raise ValueError("FAL_KEY is not configured")
    image_b64 = _load_attachment_b64(attachments[0]) if attachments else None
    if not image_b64:
        raise ValueError("Could not load attachment for fal img2img")

    payload = json.dumps({
        "prompt":                composed_prompt,
        "image_url":             f"data:image/png;base64,{image_b64}",
        "strength":              0.75,
        "num_inference_steps":   20,
        "guidance_scale":        3.5,
        "image_size":            _fal_image_size(),
        "num_images":            1,
        "enable_safety_checker": False,
    }).encode("utf-8")

    req = urllib.request.Request(
        FAL_IMG2IMG_URL,
        data=payload,
        headers={
            "Authorization": f"Key {settings.fal_key}",
            "Content-Type":  "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        resp = json.loads(r.read().decode("utf-8"))

    img_url = resp["images"][0]["url"]
    with urllib.request.urlopen(img_url, timeout=60) as img_r:
        raw = img_r.read()
    return _save_png_bytes(raw, prompt, mode, index, "fal-ai-img2img")


# ── Text-to-image backends (HuggingFace fallback chain) ───────────────────────

def _generate_huggingface_txt2img(
    composed_prompt: str, prompt: str, mode: str, index: int,
) -> tuple[str, str]:
    if not settings.hf_token:
        raise ValueError("HF_TOKEN is not configured")
    headers = {"Authorization": f"Bearer {settings.hf_token}"}
    model_path = urllib.parse.quote(settings.hf_model, safe="/")
    params = _model_specific_parameters(index)

    # ── Try fal-ai provider first (supports FLUX.1-schnell, active 2025+) ──
    fal_payload = {
        "prompt": composed_prompt,
        "num_inference_steps": params.get("num_inference_steps", 4),
        "guidance_scale": params.get("guidance_scale", 3.5),
        "width": params.get("width", 512),
        "height": params.get("height", 512),
    }
    fal_url = "https://router.huggingface.co/fal-ai/flux/schnell"
    try:
        raw = _request_bytes(fal_url, payload=fal_payload, headers=headers)
        # fal-ai returns JSON with image_url, not raw bytes
        if raw[:1] in (b'{', b'['):
            resp_json = json.loads(raw)
            img_url = None
            if isinstance(resp_json, dict):
                img_url = (resp_json.get("images") or [{}])[0].get("url") or resp_json.get("image")
            if img_url:
                with urllib.request.urlopen(img_url, timeout=60) as img_resp:
                    raw = img_resp.read()
        if len(raw) > 1000:  # plausible image
            return _save_png_bytes(raw, prompt, mode, index, "huggingface-fal")
    except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError, KeyError, IndexError, TimeoutError):
        pass

    # ── Fallback: hf-inference provider (older models / regions) ───────────
    hf_payload = {"inputs": composed_prompt, "parameters": params}
    hf_url = f"https://router.huggingface.co/hf-inference/models/{model_path}"
    try:
        raw = _request_bytes(hf_url, payload=hf_payload, headers=headers)
        return _save_png_bytes(raw, prompt, mode, index, "huggingface")
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
        pass

    # ── Fallback 2: direct inference API ────────────────────────────────────
    direct_url = f"https://api-inference.huggingface.co/models/{model_path}"
    raw = _request_bytes(direct_url, payload=hf_payload, headers=headers)
    return _save_png_bytes(raw, prompt, mode, index, "huggingface")


def _generate_a1111(
    composed_prompt: str, prompt: str, mode: str, index: int,
) -> tuple[str, str]:
    payload = {
        "prompt": composed_prompt,
        "negative_prompt": "blurry, deformed, extra fingers, low quality",
        "steps": settings.image_steps,
        "width": settings.image_width,
        "height": settings.image_height,
        "batch_size": 1,
        "cfg_scale": 7,
        "sampler_name": "Euler a",
    }
    result = _request_json(f"{settings.a1111_base_url}/sdapi/v1/txt2img", payload)
    raw = base64.b64decode(result["images"][0].split(",", 1)[0])
    return _save_png_bytes(raw, prompt, mode, index, "a1111")


def _generate_comfyui(
    composed_prompt: str, prompt: str, mode: str, index: int,
) -> tuple[str, str]:
    client_id = f"vizzy-{_slug(prompt)}-{index}"
    workflow = {
        "3": {"inputs": {"seed": _seed_for(prompt, index), "steps": settings.image_steps, "cfg": 7, "sampler_name": "euler", "scheduler": "normal", "denoise": 1, "model": ["4", 0], "positive": ["6", 0], "negative": ["7", 0], "latent_image": ["5", 0]}, "class_type": "KSampler"},
        "4": {"inputs": {"ckpt_name": "v1-5-pruned-emaonly.safetensors"}, "class_type": "CheckpointLoaderSimple"},
        "5": {"inputs": {"width": settings.image_width, "height": settings.image_height, "batch_size": 1}, "class_type": "EmptyLatentImage"},
        "6": {"inputs": {"text": composed_prompt, "clip": ["4", 1]}, "class_type": "CLIPTextEncode"},
        "7": {"inputs": {"text": "blurry, low quality, distorted", "clip": ["4", 1]}, "class_type": "CLIPTextEncode"},
        "8": {"inputs": {"samples": ["3", 0], "vae": ["4", 2]}, "class_type": "VAEDecode"},
        "9": {"inputs": {"filename_prefix": f"vizzy/{mode}-{_slug(prompt)}-{index + 1}", "images": ["8", 0]}, "class_type": "SaveImage"},
    }
    prompt_result = _request_json(f"{settings.comfyui_base_url}/prompt", {"prompt": workflow, "client_id": client_id})
    prompt_id = prompt_result["prompt_id"]
    history = _request_bytes(f"{settings.comfyui_base_url}/history/{urllib.parse.quote(prompt_id)}")
    history_data = json.loads(history.decode("utf-8"))
    outputs = history_data[prompt_id]["outputs"]
    image_meta = outputs["9"]["images"][0]
    query = urllib.parse.urlencode(image_meta)
    raw = _request_bytes(f"{settings.comfyui_base_url}/view?{query}")
    return _save_png_bytes(raw, prompt, mode, index, "comfyui")


# ── Image-to-image (real transformation) ─────────────────────────────────────
#
# Uses the HuggingFace img2img endpoint with the reference image encoded as
# base64.  Strength controls how much the model departs from the reference.
# Falls back to txt2img → SVG on any failure.

def _load_attachment_b64(attachment: dict) -> str | None:
    """
    Try to load the first attachment as base64 PNG/JPEG bytes.
    Attachment dict has keys: url, name (and optionally local_path).
    """
    local_path: str | None = attachment.get("local_path")
    if local_path:
        data = Path(local_path).read_bytes()
        return base64.b64encode(data).decode("utf-8")

    url: str | None = attachment.get("url")
    if url and url.startswith("/"):
        candidate = BASE_DIR / url.lstrip("/")
        if candidate.exists():
            return base64.b64encode(candidate.read_bytes()).decode("utf-8")

    return None


def _generate_huggingface_img2img(
    composed_prompt: str, prompt: str, mode: str, index: int,
    attachments: list[dict],
) -> tuple[str, str]:
    """
    Real image-to-image via HF Inference API (img2img endpoint).
    Sends the reference image as init_image with strength=0.75 so the model
    genuinely transforms the source rather than just treating it as a hint.
    """
    if not settings.hf_token:
        raise ValueError("HF_TOKEN is not configured")
    if not attachments:
        raise ValueError("No attachments for img2img")

    image_b64 = _load_attachment_b64(attachments[0])
    if not image_b64:
        raise ValueError("Could not load attachment for img2img")

    params = _model_specific_parameters(index)
    # img2img uses lower step count and a strength parameter
    params["strength"] = 0.75
    params["num_inference_steps"] = min(params.get("num_inference_steps", 30), 40)

    payload = {
        "inputs": composed_prompt,
        "image": image_b64,
        "parameters": params,
    }
    headers = {"Authorization": f"Bearer {settings.hf_token}"}
    model_path = urllib.parse.quote(settings.hf_model, safe="/")
    # HF img2img endpoint
    url = f"https://router.huggingface.co/hf-inference/models/{model_path}/image-to-image"
    raw = _request_bytes(url, payload=payload, headers=headers)
    return _save_png_bytes(raw, prompt, mode, index, "huggingface-img2img")


def _generate_a1111_img2img(
    composed_prompt: str, prompt: str, mode: str, index: int,
    attachments: list[dict],
) -> tuple[str, str]:
    """img2img via Automatic1111 /sdapi/v1/img2img."""
    image_b64 = _load_attachment_b64(attachments[0]) if attachments else None
    if not image_b64:
        raise ValueError("Could not load attachment for a1111 img2img")
    payload = {
        "init_images": [image_b64],
        "prompt": composed_prompt,
        "negative_prompt": "blurry, deformed, extra fingers, low quality",
        "denoising_strength": 0.75,
        "steps": settings.image_steps,
        "width": settings.image_width,
        "height": settings.image_height,
        "cfg_scale": 7,
        "sampler_name": "Euler a",
    }
    result = _request_json(f"{settings.a1111_base_url}/sdapi/v1/img2img", payload)
    raw = base64.b64decode(result["images"][0].split(",", 1)[0])
    return _save_png_bytes(raw, prompt, mode, index, "a1111-img2img")


# ── Video generation (clean stub, ready for wiring) ───────────────────────────
#
# Video synthesis is not yet wired to a live backend.
# When a backend becomes available (Replicate AnimateDiff, Stable Video
# Diffusion, RunwayML, etc.) replace _generate_video_stub with a real call
# and update SUPPORTED_VIDEO_BACKENDS below.
#
# The stub returns a placeholder SVG marked as "Motion Board" so the UI
# correctly labels it, and records a video job in the DB for async pickup.

SUPPORTED_VIDEO_BACKENDS: list[str] = []   # e.g. ["replicate", "runwayml"]


def _generate_video_stub(
    prompt: str, mode: str, index: int, memory_keywords: list[str],
) -> tuple[str, str]:
    """
    Placeholder until a video backend is configured.
    Writes a motion-tagged SVG with an overlay note.
    """
    filename, _ = _write_svg(prompt, mode, index, memory_keywords)
    # Overwrite with a motion-label variant
    filepath = GENERATED_DIR / filename
    svg = filepath.read_text(encoding="utf-8")
    svg = svg.replace("ATELIERAI", "ATELIER MOTION")
    svg = svg.replace("Emotional composition" if mode == "home" else "Brand composition",
                      "Motion Concept — Video backend not yet configured")
    filepath.write_text(svg, encoding="utf-8")
    return filename, "video-stub"


# ── Orchestration router ──────────────────────────────────────────────────────

def _render_file(
    prompt: str, mode: str, index: int,
    memory_keywords: list[str], attachments: list[dict],
    task_type: str, brand_context: dict | None,
) -> tuple[str, str]:
    """
    Route to the correct pipeline based on task_type, then fall back
    gracefully: real backend → txt2img → SVG.
    """
    composed = _compose_prompt(prompt, mode, memory_keywords, attachments, index, brand_context)
    backend = settings.image_backend.lower()

    # ── VIDEO ─────────────────────────────────────────────────────────────────
    if task_type == TaskType.VIDEO:
        return _generate_video_stub(prompt, mode, index, memory_keywords)

    # ── IMAGE-TO-IMAGE ────────────────────────────────────────────────────────
    if task_type == TaskType.IMAGE_TO_IMAGE and attachments:
        try:
            if settings.fal_key:                          # fal.ai first
                return _generate_fal_img2img(composed, prompt, mode, index, attachments)
            if backend == "huggingface":
                return _generate_huggingface_img2img(composed, prompt, mode, index, attachments)
            if backend == "a1111":
                return _generate_a1111_img2img(composed, prompt, mode, index, attachments)
        except (KeyError, IndexError, ValueError, urllib.error.URLError,
                urllib.error.HTTPError, TimeoutError, json.JSONDecodeError):
            pass
        # Fallback: txt2img with reference hint in prompt
        composed_fallback = composed + ", incorporate the style and composition of the reference image"
        try:
            if settings.fal_key:
                return _generate_fal_txt2img(composed_fallback, prompt, mode, index)
            if backend == "huggingface":
                return _generate_huggingface_txt2img(composed_fallback, prompt, mode, index)
            if backend == "a1111":
                return _generate_a1111(composed_fallback, prompt, mode, index)
        except (KeyError, IndexError, ValueError, urllib.error.URLError,
                urllib.error.HTTPError, TimeoutError, json.JSONDecodeError):
            pass
        return _write_svg(prompt, mode, index, memory_keywords)

    # ── TEXT-TO-IMAGE, POSTER, STORY ─────────────────────────────────────────
    try:
        if settings.fal_key:                              # fal.ai first
            return _generate_fal_txt2img(composed, prompt, mode, index)
        if backend == "huggingface":
            return _generate_huggingface_txt2img(composed, prompt, mode, index)
        if backend == "a1111":
            return _generate_a1111(composed, prompt, mode, index)
        if backend == "comfyui":
            return _generate_comfyui(composed, prompt, mode, index)
    except (KeyError, IndexError, ValueError, urllib.error.URLError,
            urllib.error.HTTPError, TimeoutError, json.JSONDecodeError):
        pass

    return _write_svg(prompt, mode, index, memory_keywords)


# ── Public API ────────────────────────────────────────────────────────────────

def generate_assets(
    prompt: str,
    mode: str,
    count: int = 3,
    memory_keywords: list[str] | None = None,
    attachments: list[dict] | None = None,
    brand_context: dict | None = None,
) -> list[dict]:
    ensure_generated_dir()
    memory_keywords = memory_keywords or []
    attachments = attachments or []

    task_type = detect_task_type(prompt, attachments)
    assets: list[dict] = []
    last_backend: str = ""

    for index in range(count):
        # Add delay between consecutive Groq AI-SVG calls to avoid CF rate-limit
        if index > 0 and last_backend == "groq-svg":
            time.sleep(1.2)

        filename, backend = _render_file(
            prompt, mode, index, memory_keywords, attachments, task_type, brand_context
        )
        last_backend = backend
        asset_type = _asset_type(prompt, mode, index)
        assets.append({
            "type": asset_type,
            "title": _asset_title(mode, asset_type, index),
            "description": _asset_description(
                mode, prompt, backend, memory_keywords,
                bool(attachments), index, task_type,
            ),
            "preview_url": f"/generated/{filename}",
            "filename": filename,
            "task_type": task_type,
            "actions": _asset_actions(mode, asset_type),
        })

    return assets