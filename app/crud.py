from __future__ import annotations

import json
from collections import Counter
from datetime import UTC, datetime

from app.db import get_connection


STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "create", "do", "for", "from", "how",
    "i", "if", "in", "into", "is", "it", "like", "make", "me", "my", "of", "on", "or", "show",
    "something", "that", "the", "this", "to", "turn", "up", "use", "visual", "with", "without", "your",
}


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _extract_keywords(text: str) -> list[str]:
    tokens = []
    for raw in text.lower().replace("\n", " ").split():
        token = "".join(char for char in raw if char.isalnum() or char == "-").strip("-")
        if len(token) < 3 or token in STOPWORDS:
            continue
        tokens.append(token)
    counts = Counter(tokens)
    return [token for token, _ in counts.most_common(8)]


# ── Conversations ─────────────────────────────────────────────────────────────

def list_conversations() -> list[dict]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT c.id, c.title, c.mode, c.created_at,
                   COUNT(m.id) AS message_count
            FROM conversations c
            LEFT JOIN messages m ON m.conversation_id = c.id
            GROUP BY c.id
            ORDER BY c.id DESC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def get_conversation(conversation_id: int) -> dict | None:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT id, title, mode, created_at FROM conversations WHERE id = ?",
            (conversation_id,),
        ).fetchone()
    return dict(row) if row else None


def create_conversation(title: str, mode: str) -> dict:
    created_at = _utc_now()
    with get_connection() as connection:
        cursor = connection.execute(
            "INSERT INTO conversations (title, mode, created_at) VALUES (?, ?, ?)",
            (title, mode, created_at),
        )
        connection.commit()
        conversation_id = cursor.lastrowid
    return {"id": conversation_id, "title": title, "mode": mode, "created_at": created_at}


# ── Messages ──────────────────────────────────────────────────────────────────

def add_message(
    conversation_id: int,
    role: str,
    tag: str,
    text: str,
    assets: list[dict] | None = None,
    attachments: list[dict] | None = None,
) -> dict:
    created_at = _utc_now()
    assets_json = json.dumps(assets or [])
    attachments_json = json.dumps(attachments or [])
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO messages (conversation_id, role, tag, text, created_at, assets_json, attachments_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (conversation_id, role, tag, text, created_at, assets_json, attachments_json),
        )
        connection.commit()
        message_id = cursor.lastrowid
    return {
        "id": message_id,
        "conversation_id": conversation_id,
        "role": role,
        "tag": tag,
        "text": text,
        "created_at": created_at,
        "assets": assets or [],
        "attachments": attachments or [],
    }


def get_messages(conversation_id: int) -> list[dict]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, conversation_id, role, tag, text, created_at, assets_json, attachments_json
            FROM messages
            WHERE conversation_id = ?
            ORDER BY id ASC
            """,
            (conversation_id,),
        ).fetchall()

    messages: list[dict] = []
    for row in rows:
        item = dict(row)
        item["assets"] = json.loads(item.pop("assets_json") or "[]")
        item["attachments"] = json.loads(item.pop("attachments_json") or "[]")
        messages.append(item)
    return messages


# ── Lightweight keyword memory (original, kept for compatibility) ──────────────

def update_memory(mode: str, prompt: str) -> dict:
    updated_at = _utc_now()
    new_keywords = _extract_keywords(prompt)
    with get_connection() as connection:
        row = connection.execute(
            "SELECT keywords_json FROM memories WHERE mode = ?", (mode,)
        ).fetchone()
        existing = json.loads(row[0]) if row else []
        merged: list[str] = []
        for kw in existing + new_keywords:
            if kw not in merged:
                merged.append(kw)
        merged = merged[:12]
        connection.execute(
            """
            INSERT INTO memories (mode, keywords_json, updated_at) VALUES (?, ?, ?)
            ON CONFLICT(mode) DO UPDATE SET keywords_json = excluded.keywords_json,
                                            updated_at    = excluded.updated_at
            """,
            (mode, json.dumps(merged), updated_at),
        )
        connection.commit()
    return {"mode": mode, "keywords": merged, "updated_at": updated_at}


def get_memory(mode: str) -> dict:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT keywords_json, updated_at FROM memories WHERE mode = ?", (mode,)
        ).fetchone()
    if not row:
        return {"mode": mode, "keywords": [], "updated_at": None}
    return {"mode": mode, "keywords": json.loads(row[0]), "updated_at": row[1]}


# ── Home: rich style profile ──────────────────────────────────────────────────

def get_home_profile() -> dict:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM home_profiles ORDER BY id DESC LIMIT 1"
        ).fetchone()
    if not row:
        return {
            "style_selections": [],
            "favourite_asset_ids": [],
            "feedback_signals": [],
            "mood_keywords": [],
            "colour_palette": [],
            "updated_at": None,
        }
    item = dict(row)
    for key in ("style_selections", "favourite_asset_ids", "feedback_signals", "mood_keywords", "colour_palette"):
        item[key] = json.loads(item.get(key) or "[]")
    return item


def update_home_profile(
    style_selection: str | None = None,
    favourite_asset_id: str | None = None,
    feedback: dict | None = None,       # {prompt, asset, signal: like|dislike|refine}
    mood_keywords: list[str] | None = None,
    colour_palette: list[str] | None = None,
) -> dict:
    profile = get_home_profile()
    updated_at = _utc_now()

    if style_selection and style_selection not in profile["style_selections"]:
        profile["style_selections"].append(style_selection)

    if favourite_asset_id and favourite_asset_id not in profile["favourite_asset_ids"]:
        profile["favourite_asset_ids"].append(favourite_asset_id)

    if feedback:
        profile["feedback_signals"].append(feedback)
        profile["feedback_signals"] = profile["feedback_signals"][-50:]  # keep last 50

    if mood_keywords:
        for kw in mood_keywords:
            if kw not in profile["mood_keywords"]:
                profile["mood_keywords"].append(kw)
        profile["mood_keywords"] = profile["mood_keywords"][:20]

    if colour_palette:
        for colour in colour_palette:
            if colour not in profile["colour_palette"]:
                profile["colour_palette"].append(colour)
        profile["colour_palette"] = profile["colour_palette"][:10]

    with get_connection() as connection:
        row = connection.execute(
            "SELECT id FROM home_profiles ORDER BY id DESC LIMIT 1"
        ).fetchone()
        payload = (
            json.dumps(profile["style_selections"]),
            json.dumps(profile["favourite_asset_ids"]),
            json.dumps(profile["feedback_signals"]),
            json.dumps(profile["mood_keywords"]),
            json.dumps(profile["colour_palette"]),
            updated_at,
        )
        if row:
            connection.execute(
                """
                UPDATE home_profiles SET style_selections=?, favourite_asset_ids=?,
                  feedback_signals=?, mood_keywords=?, colour_palette=?, updated_at=?
                WHERE id=?
                """,
                (*payload, row["id"]),
            )
        else:
            connection.execute(
                """
                INSERT INTO home_profiles
                  (style_selections, favourite_asset_ids, feedback_signals,
                   mood_keywords, colour_palette, updated_at)
                VALUES (?,?,?,?,?,?)
                """,
                payload,
            )
        connection.commit()

    profile["updated_at"] = updated_at
    return profile


def record_feedback(prompt: str, asset_filename: str, signal: str) -> dict:
    """signal: 'like' | 'dislike' | 'refine'"""
    mood = _extract_keywords(prompt) if signal == "like" else []
    return update_home_profile(
        feedback={"prompt": prompt, "asset": asset_filename, "signal": signal},
        mood_keywords=mood,
    )


# ── Business: brand kit / profile ─────────────────────────────────────────────

def get_business_profile(slug: str = "default") -> dict:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM business_profiles WHERE slug = ?", (slug,)
        ).fetchone()
    if not row:
        return {
            "slug": slug,
            "business_name": "",
            "business_type": "",
            "brand_voice": "",
            "primary_colours": [],
            "secondary_colours": [],
            "logo_url": "",
            "font_preference": "",
            "tagline": "",
            "values_keywords": [],
            "updated_at": None,
        }
    item = dict(row)
    for key in ("primary_colours", "secondary_colours", "values_keywords"):
        item[key] = json.loads(item.get(key) or "[]")
    return item


def upsert_business_profile(slug: str = "default", **fields) -> dict:
    """
    Accepted fields: business_name, business_type, brand_voice,
    primary_colours (list), secondary_colours (list), logo_url,
    font_preference, tagline, values_keywords (list).
    """
    profile = get_business_profile(slug)
    updated_at = _utc_now()

    for key, value in fields.items():
        if key in ("primary_colours", "secondary_colours", "values_keywords"):
            if isinstance(value, list):
                profile[key] = value
        elif key in profile:
            profile[key] = value

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO business_profiles
              (slug, business_name, business_type, brand_voice,
               primary_colours, secondary_colours, logo_url,
               font_preference, tagline, values_keywords, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(slug) DO UPDATE SET
              business_name     = excluded.business_name,
              business_type     = excluded.business_type,
              brand_voice       = excluded.brand_voice,
              primary_colours   = excluded.primary_colours,
              secondary_colours = excluded.secondary_colours,
              logo_url          = excluded.logo_url,
              font_preference   = excluded.font_preference,
              tagline           = excluded.tagline,
              values_keywords   = excluded.values_keywords,
              updated_at        = excluded.updated_at
            """,
            (
                slug,
                profile["business_name"],
                profile["business_type"],
                profile["brand_voice"],
                json.dumps(profile["primary_colours"]),
                json.dumps(profile["secondary_colours"]),
                profile["logo_url"],
                profile["font_preference"],
                profile["tagline"],
                json.dumps(profile["values_keywords"]),
                updated_at,
            ),
        )
        connection.commit()
    profile["updated_at"] = updated_at
    return profile


# ── Business: campaigns ───────────────────────────────────────────────────────

def list_campaigns(business_slug: str = "default") -> list[dict]:
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT * FROM campaigns WHERE business_slug = ? ORDER BY id DESC",
            (business_slug,),
        ).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        for key in ("surfaces", "asset_ids", "copy_snippets"):
            item[key] = json.loads(item.get(key) or "[]")
        result.append(item)
    return result


def create_campaign(
    name: str,
    goal: str = "",
    season: str = "",
    surfaces: list[str] | None = None,
    business_slug: str = "default",
) -> dict:
    now = _utc_now()
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO campaigns (business_slug, name, goal, season, surfaces,
                                   status, asset_ids, copy_snippets, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, 'draft', '[]', '[]', ?, ?)
            """,
            (business_slug, name, goal, season, json.dumps(surfaces or []), now, now),
        )
        connection.commit()
        campaign_id = cursor.lastrowid
    return {
        "id": campaign_id, "business_slug": business_slug, "name": name,
        "goal": goal, "season": season, "surfaces": surfaces or [],
        "status": "draft", "asset_ids": [], "copy_snippets": [],
        "created_at": now, "updated_at": now,
    }


def update_campaign_assets(
    campaign_id: int,
    asset_filenames: list[str] | None = None,
    copy_snippets: list[str] | None = None,
) -> dict | None:
    now = _utc_now()
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM campaigns WHERE id = ?", (campaign_id,)
        ).fetchone()
        if not row:
            return None
        item = dict(row)
        existing_assets = json.loads(item["asset_ids"] or "[]")
        existing_copy   = json.loads(item["copy_snippets"] or "[]")
        merged_assets = list(dict.fromkeys(existing_assets + (asset_filenames or [])))
        merged_copy   = list(dict.fromkeys(existing_copy   + (copy_snippets   or [])))
        connection.execute(
            "UPDATE campaigns SET asset_ids=?, copy_snippets=?, updated_at=? WHERE id=?",
            (json.dumps(merged_assets), json.dumps(merged_copy), now, campaign_id),
        )
        connection.commit()
    item["asset_ids"]    = merged_assets
    item["copy_snippets"] = merged_copy
    item["updated_at"]   = now
    for key in ("surfaces",):
        item[key] = json.loads(item.get(key) or "[]")
    return item


# ── Export records ────────────────────────────────────────────────────────────

def record_export(conversation_id: int | None, surface: str, file_path: str) -> dict:
    now = _utc_now()
    with get_connection() as connection:
        cursor = connection.execute(
            "INSERT INTO exports (conversation_id, surface, file_path, created_at) VALUES (?,?,?,?)",
            (conversation_id, surface, file_path, now),
        )
        connection.commit()
        export_id = cursor.lastrowid
    return {
        "id": export_id,
        "conversation_id": conversation_id,
        "surface": surface,
        "file_path": file_path,
        "created_at": now,
    }


def list_exports(conversation_id: int | None = None) -> list[dict]:
    with get_connection() as connection:
        if conversation_id is not None:
            rows = connection.execute(
                "SELECT * FROM exports WHERE conversation_id = ? ORDER BY id DESC",
                (conversation_id,),
            ).fetchall()
        else:
            rows = connection.execute(
                "SELECT * FROM exports ORDER BY id DESC LIMIT 50"
            ).fetchall()
    return [dict(row) for row in rows]


# ── Video jobs ────────────────────────────────────────────────────────────────

def create_video_job(
    prompt: str,
    mode: str,
    conversation_id: int | None = None,
    backend: str = "",
) -> dict:
    now = _utc_now()
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO video_jobs
              (conversation_id, prompt, mode, status, backend, created_at, updated_at)
            VALUES (?,?,?,'pending',?,?,?)
            """,
            (conversation_id, prompt, mode, backend, now, now),
        )
        connection.commit()
        job_id = cursor.lastrowid
    return {
        "id": job_id, "conversation_id": conversation_id, "prompt": prompt,
        "mode": mode, "status": "pending", "backend": backend,
        "output_url": "", "error_message": "", "created_at": now, "updated_at": now,
    }


def update_video_job(job_id: int, status: str, output_url: str = "", error_message: str = "") -> dict | None:
    now = _utc_now()
    with get_connection() as connection:
        connection.execute(
            "UPDATE video_jobs SET status=?, output_url=?, error_message=?, updated_at=? WHERE id=?",
            (status, output_url, error_message, now, job_id),
        )
        connection.commit()
        row = connection.execute("SELECT * FROM video_jobs WHERE id=?", (job_id,)).fetchone()
    return dict(row) if row else None