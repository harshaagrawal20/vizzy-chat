from __future__ import annotations

import json
from datetime import UTC, datetime

from app.db import get_connection


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


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
    return {
        "id": conversation_id,
        "title": title,
        "mode": mode,
        "created_at": created_at,
    }


def add_message(
    conversation_id: int,
    role: str,
    tag: str,
    text: str,
    assets: list[dict] | None = None,
) -> dict:
    created_at = _utc_now()
    assets_json = json.dumps(assets or [])
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO messages (conversation_id, role, tag, text, created_at, assets_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (conversation_id, role, tag, text, created_at, assets_json),
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
    }


def get_messages(conversation_id: int) -> list[dict]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, conversation_id, role, tag, text, created_at, assets_json
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
        messages.append(item)
    return messages
