from __future__ import annotations

from textwrap import shorten

from app.services.generator import generate_assets


def suggest_title(prompt: str, mode: str) -> str:
    prefix = "Home" if mode == "home" else "Business"
    return f"{prefix}: {shorten(prompt, width=36, placeholder='...')}"


def build_assistant_reply(prompt: str, mode: str) -> tuple[str, str, list[dict]]:
    lowered = prompt.lower()
    assets = generate_assets(prompt=prompt, mode=mode, count=3)

    if mode == "home":
        tag = "Generated response"
        if "story" in lowered or "kids" in lowered:
            text = (
                "I turned your request into a story-led visual set with multiple scene directions, "
                "so you can keep the narrative and artwork evolving together."
            )
        elif "quote" in lowered or "poster" in lowered:
            text = (
                "I interpreted this as a personal poster request and created several visual directions "
                "that can be refined into a living room print or framed display."
            )
        else:
            text = (
                "I interpreted your request as a personal creative exploration and created a small set "
                "of visual directions so you can compare, refine, and save your preferred style."
            )
    else:
        tag = "Asset response"
        if "poster" in lowered or "signage" in lowered:
            text = (
                "I treated this as a business signage request and created reusable variants that can fit "
                "in-store display, frame output, or quick campaign adaptation."
            )
        elif "video" in lowered or "loop" in lowered:
            text = (
                "I treated this as a motion-led creative brief and created key visual boards that can guide "
                "a simple loop, promo animation, or campaign sequence."
            )
        else:
            text = (
                "I interpreted this as a brand-facing creative brief and created a set of reusable assets "
                "that can be refined for frame, social, or lightweight campaign use."
            )

    return tag, text, assets
