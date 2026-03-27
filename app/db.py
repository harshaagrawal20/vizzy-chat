from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "vizzy.db"


def _ensure_column(connection: sqlite3.Connection, table: str, column: str, ddl: str) -> None:
    columns = {
        row[1]
        for row in connection.execute(f"PRAGMA table_info({table})").fetchall()
    }
    if column not in columns:
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")


def init_db() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as connection:

        # ── Core conversation tables ───────────────────────────────────────────
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                title       TEXT    NOT NULL,
                mode        TEXT    NOT NULL,
                created_at  TEXT    NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id   INTEGER NOT NULL,
                role              TEXT    NOT NULL,
                tag               TEXT    NOT NULL,
                text              TEXT    NOT NULL,
                created_at        TEXT    NOT NULL,
                assets_json       TEXT,
                attachments_json  TEXT,
                FOREIGN KEY (conversation_id) REFERENCES conversations (id)
            )
            """
        )

        # ── Lightweight keyword memory (original) ─────────────────────────────
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS memories (
                mode          TEXT PRIMARY KEY,
                keywords_json TEXT NOT NULL,
                updated_at    TEXT NOT NULL
            )
            """
        )

        # ── Home: rich style profile ───────────────────────────────────────────
        # Stores aesthetic selections, favourite outputs, and feedback signals
        # so the home user's taste is remembered across sessions.
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS home_profiles (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                style_selections    TEXT    DEFAULT '[]',   -- JSON list of style labels chosen by user
                favourite_asset_ids TEXT    DEFAULT '[]',   -- JSON list of asset filenames marked as favourite
                feedback_signals    TEXT    DEFAULT '[]',   -- JSON list of {prompt, asset, signal: like|dislike|refine}
                mood_keywords       TEXT    DEFAULT '[]',   -- JSON list of mood/emotion words extracted from liked outputs
                colour_palette      TEXT    DEFAULT '[]',   -- JSON list of hex colours extracted from liked visuals
                updated_at          TEXT    NOT NULL
            )
            """
        )

        # ── Business: brand kit ───────────────────────────────────────────────
        # One row per business (single-tenant for now; keyed by a stable slug).
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS business_profiles (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                slug              TEXT    UNIQUE NOT NULL DEFAULT 'default',
                business_name     TEXT    DEFAULT '',
                business_type     TEXT    DEFAULT '',   -- e.g. restaurant, retail, cafe
                brand_voice       TEXT    DEFAULT '',   -- e.g. premium, warm, playful
                primary_colours   TEXT    DEFAULT '[]', -- JSON list of hex strings
                secondary_colours TEXT    DEFAULT '[]',
                logo_url          TEXT    DEFAULT '',   -- path to uploaded logo file
                font_preference   TEXT    DEFAULT '',
                tagline           TEXT    DEFAULT '',
                values_keywords   TEXT    DEFAULT '[]', -- JSON list e.g. ["sustainable","local","artisan"]
                updated_at        TEXT    NOT NULL
            )
            """
        )

        # ── Business: campaigns ───────────────────────────────────────────────
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS campaigns (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                business_slug   TEXT    NOT NULL DEFAULT 'default',
                name            TEXT    NOT NULL,
                goal            TEXT    DEFAULT '',   -- e.g. awareness, conversion, seasonal
                season          TEXT    DEFAULT '',   -- e.g. Diwali, monsoon, summer
                surfaces        TEXT    DEFAULT '[]', -- JSON list: frame, social, email, print
                status          TEXT    DEFAULT 'draft',  -- draft | active | archived
                asset_ids       TEXT    DEFAULT '[]', -- JSON list of generated asset filenames
                copy_snippets   TEXT    DEFAULT '[]', -- JSON list of generated copy strings
                created_at      TEXT    NOT NULL,
                updated_at      TEXT    NOT NULL
            )
            """
        )

        # ── Export / deploy records ───────────────────────────────────────────
        # Tracks every file export so the user can re-download or review history.
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS exports (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER,
                surface         TEXT    NOT NULL,  -- frame | social | email | print | zip
                file_path       TEXT    NOT NULL,
                created_at      TEXT    NOT NULL
            )
            """
        )

        # ── Video generation jobs ─────────────────────────────────────────────
        # Tracks video requests; backend field identifies the pipeline when wired.
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS video_jobs (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER,
                prompt          TEXT    NOT NULL,
                mode            TEXT    NOT NULL,
                status          TEXT    NOT NULL DEFAULT 'pending',  -- pending | processing | done | failed
                backend         TEXT    DEFAULT '',   -- animatediff | stable-video | replicate | etc.
                output_url      TEXT    DEFAULT '',
                error_message   TEXT    DEFAULT '',
                created_at      TEXT    NOT NULL,
                updated_at      TEXT    NOT NULL
            )
            """
        )

        # ── Migrations: add columns to existing installs ──────────────────────
        _ensure_column(connection, "messages",  "attachments_json", "TEXT")
        _ensure_column(connection, "conversations", "updated_at",   "TEXT")

        connection.commit()


@contextmanager
def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
    finally:
        connection.close()