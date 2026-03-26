from __future__ import annotations

import hashlib
import html
import random
from pathlib import Path
from textwrap import shorten


BASE_DIR = Path(__file__).resolve().parent.parent.parent
GENERATED_DIR = BASE_DIR / "generated"


PALETTES = [
    ("#35140f", "#bb4f2b", "#f0b56e", "#fff2da"),
    ("#102542", "#1f5f8b", "#8cc8ff", "#ecf8ff"),
    ("#17341f", "#3a7d44", "#a1d99b", "#f3fff3"),
    ("#421322", "#8c2f5f", "#f4b6d2", "#fff2f8"),
    ("#332038", "#6a4c93", "#f2a6ff", "#faf0ff"),
]


def ensure_generated_dir() -> None:
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)


def _seed_for(prompt: str, variant: int) -> int:
    digest = hashlib.sha256(f"{prompt}:{variant}".encode("utf-8")).hexdigest()
    return int(digest[:16], 16)


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


def _asset_description(mode: str, prompt: str) -> str:
    prefix = (
        "Built to feel personal, symbolic, and open to refinement."
        if mode == "home"
        else "Built to feel branded, reusable, and deployable across surfaces."
    )
    suffix = shorten(prompt, width=88, placeholder="...")
    return f"{prefix} Prompt focus: {suffix}"


def _asset_actions(mode: str) -> list[dict]:
    if mode == "home":
        labels = ["Refine", "Generate more", "Save style"]
    else:
        labels = ["Refine", "Export", "Use on frame"]
    return [{"label": label} for label in labels]


def _svg_markup(prompt: str, mode: str, variant: int) -> str:
    seed = _seed_for(prompt, variant)
    randomizer = random.Random(seed)
    colors = PALETTES[seed % len(PALETTES)]
    label = html.escape(shorten(prompt, width=80, placeholder="..."))

    circles = []
    for _ in range(7):
        radius = randomizer.randint(80, 220)
        x = randomizer.randint(40, 980)
        y = randomizer.randint(40, 980)
        opacity = randomizer.uniform(0.12, 0.32)
        fill = colors[randomizer.randint(0, len(colors) - 1)]
        circles.append(
            f'<circle cx="{x}" cy="{y}" r="{radius}" fill="{fill}" opacity="{opacity:.2f}" />'
        )

    lines = []
    for _ in range(6):
        x1 = randomizer.randint(0, 1024)
        y1 = randomizer.randint(0, 1024)
        x2 = randomizer.randint(0, 1024)
        y2 = randomizer.randint(0, 1024)
        stroke = colors[randomizer.randint(0, len(colors) - 1)]
        width = randomizer.randint(2, 8)
        opacity = randomizer.uniform(0.18, 0.42)
        lines.append(
            f'<path d="M {x1} {y1} Q {randomizer.randint(0, 1024)} {randomizer.randint(0, 1024)} {x2} {y2}" '
            f'stroke="{stroke}" stroke-width="{width}" stroke-linecap="round" fill="none" opacity="{opacity:.2f}" />'
        )

    subtitle = "Home expression engine" if mode == "home" else "Business creative engine"
    return f"""<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"1024\" height=\"1024\" viewBox=\"0 0 1024 1024\" role=\"img\" aria-label=\"{label}\">\n  <defs>\n    <linearGradient id=\"grad-{seed}\" x1=\"0%\" y1=\"0%\" x2=\"100%\" y2=\"100%\">\n      <stop offset=\"0%\" stop-color=\"{colors[0]}\" />\n      <stop offset=\"45%\" stop-color=\"{colors[1]}\" />\n      <stop offset=\"100%\" stop-color=\"{colors[2]}\" />\n    </linearGradient>\n    <filter id=\"blur-{seed}\">\n      <feGaussianBlur stdDeviation=\"12\" />\n    </filter>\n  </defs>\n  <rect width=\"1024\" height=\"1024\" fill=\"url(#grad-{seed})\" />\n  <g filter=\"url(#blur-{seed})\">\n    {''.join(circles)}\n  </g>\n  <g>\n    {''.join(lines)}\n  </g>\n  <rect x=\"56\" y=\"720\" width=\"912\" height=\"232\" rx=\"28\" fill=\"{colors[3]}\" opacity=\"0.86\" />\n  <text x=\"92\" y=\"790\" fill=\"{colors[0]}\" font-size=\"28\" font-family=\"Arial, sans-serif\" letter-spacing=\"4\">VIZZY CHAT</text>\n  <text x=\"92\" y=\"838\" fill=\"{colors[0]}\" font-size=\"48\" font-weight=\"700\" font-family=\"Arial, sans-serif\">{label}</text>\n  <text x=\"92\" y=\"896\" fill=\"{colors[1]}\" font-size=\"24\" font-family=\"Arial, sans-serif\">{subtitle}</text>\n  <text x=\"92\" y=\"934\" fill=\"{colors[1]}\" font-size=\"20\" font-family=\"Arial, sans-serif\">Variant {variant + 1} - Free CPU render - SVG output</text>\n</svg>\n"""


def generate_assets(prompt: str, mode: str, count: int = 3) -> list[dict]:
    ensure_generated_dir()
    assets: list[dict] = []
    slug = hashlib.sha1(prompt.encode("utf-8")).hexdigest()[:10]
    for index in range(count):
        filename = f"{mode}-{slug}-{index + 1}.svg"
        filepath = GENERATED_DIR / filename
        filepath.write_text(_svg_markup(prompt, mode, index), encoding="utf-8")
        asset_type = _asset_type(prompt, mode, index)
        assets.append(
            {
                "type": asset_type,
                "title": _asset_title(mode, asset_type, index),
                "description": _asset_description(mode, prompt),
                "preview_url": f"/generated/{filename}",
                "actions": _asset_actions(mode),
            }
        )
    return assets
