"""
SQLite database layer — replaces JSON file storage for conversations.

Uses sqlite3 from the Python standard library (no extra dependencies).
Database file: backend/data/english_practice.db
"""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

DATA_DIR = Path(__file__).parent / "data"
DB_PATH = DATA_DIR / "english_practice.db"

# ---------------------------------------------------------------------------
# Connection helper
# ---------------------------------------------------------------------------


def _connect() -> sqlite3.Connection:
    """Create a new connection with row-factory for dict-like access."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------


def init_db() -> None:
    """Create tables if they don't already exist."""
    conn = _connect()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS conversations (
            session_id   TEXT PRIMARY KEY,
            scene_id     TEXT NOT NULL,
            created_at   TEXT NOT NULL,
            ended_at     TEXT,
            summary_json TEXT
        );

        CREATE TABLE IF NOT EXISTS turns (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id          TEXT NOT NULL,
            turn_number         INTEGER NOT NULL,
            user_text           TEXT NOT NULL DEFAULT '',
            corrected_text      TEXT NOT NULL DEFAULT '',
            ai_text             TEXT NOT NULL,
            corrections_json    TEXT NOT NULL DEFAULT '[]',
            pronunciation_score REAL,
            pronunciation_note  TEXT NOT NULL DEFAULT '',
            FOREIGN KEY (session_id) REFERENCES conversations(session_id)
        );

        CREATE INDEX IF NOT EXISTS idx_turns_session ON turns(session_id);
    """)
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Conversations CRUD
# ---------------------------------------------------------------------------


def create_conversation(session_id: str, scene_id: str) -> dict:
    """Insert a new conversation record. Returns the created doc."""
    now = datetime.now(timezone.utc).isoformat()
    conn = _connect()
    conn.execute(
        "INSERT INTO conversations (session_id, scene_id, created_at) VALUES (?, ?, ?)",
        (session_id, scene_id, now),
    )
    conn.commit()
    conn.close()
    return {
        "session_id": session_id,
        "scene_id": scene_id,
        "created_at": now,
        "ended_at": None,
        "messages": [],
    }


def get_conversation(session_id: str) -> Optional[dict]:
    """Load a full conversation with all turns."""
    conn = _connect()
    conv_row = conn.execute(
        "SELECT * FROM conversations WHERE session_id = ?", (session_id,)
    ).fetchone()
    if conv_row is None:
        conn.close()
        return None

    turn_rows = conn.execute(
        "SELECT * FROM turns WHERE session_id = ? ORDER BY turn_number",
        (session_id,),
    ).fetchall()
    conn.close()

    messages = []
    for t in turn_rows:
        messages.append({
            "turn": t["turn_number"],
            "user_text": t["user_text"],
            "corrected_text": t["corrected_text"],
            "ai_text": t["ai_text"],
            "corrections": json.loads(t["corrections_json"]),
            "pronunciation_score": (
                json.loads(t["pronunciation_score"])
                if t["pronunciation_score"]
                else None
            ),
            "pronunciation_note": t["pronunciation_note"],
        })

    doc = {
        "session_id": conv_row["session_id"],
        "scene_id": conv_row["scene_id"],
        "created_at": conv_row["created_at"],
        "ended_at": conv_row["ended_at"],
        "messages": messages,
    }
    if conv_row["summary_json"]:
        doc["summary"] = json.loads(conv_row["summary_json"])
    return doc


def list_conversations(limit: int = 20) -> list[dict]:
    """List recent conversations with turn counts."""
    conn = _connect()
    rows = conn.execute(
        """
        SELECT c.session_id, c.scene_id, c.created_at, c.ended_at, c.summary_json,
               COUNT(t.id) AS turn_count
        FROM conversations c
        LEFT JOIN turns t ON t.session_id = c.session_id
        GROUP BY c.session_id
        ORDER BY c.created_at DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    conn.close()
    return [
        {
            "session_id": r["session_id"],
            "scene_id": r["scene_id"],
            "created_at": r["created_at"],
            "ended_at": r["ended_at"],
            "has_summary": r["summary_json"] is not None,
            "turn_count": r["turn_count"],
        }
        for r in rows
    ]


def append_turn(session_id: str, turn_data: dict) -> None:
    """Add a single conversation turn."""
    conn = _connect()
    score = turn_data.get("pronunciation_score")
    conn.execute(
        """
        INSERT INTO turns (session_id, turn_number, user_text, corrected_text,
                           ai_text, corrections_json, pronunciation_score, pronunciation_note)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            session_id,
            turn_data["turn"],
            turn_data.get("user_text", ""),
            turn_data.get("corrected_text", ""),
            turn_data.get("ai_text", ""),
            json.dumps(turn_data.get("corrections", []), ensure_ascii=False),
            json.dumps(score) if score else None,
            turn_data.get("pronunciation_note", ""),
        ),
    )
    conn.commit()
    conn.close()


def delete_conversation(session_id: str) -> bool:
    """Delete a conversation and all its turns. Returns True if found & deleted."""
    conn = _connect()
    conn.execute("DELETE FROM turns WHERE session_id = ?", (session_id,))
    conn.execute("DELETE FROM conversations WHERE session_id = ?", (session_id,))
    deleted = conn.total_changes > 0
    conn.commit()
    conn.close()
    return deleted


def end_conversation(session_id: str, summary: dict) -> dict:
    """Mark a conversation as ended and store the summary."""
    now = datetime.now(timezone.utc).isoformat()
    conn = _connect()
    conn.execute(
        "UPDATE conversations SET ended_at = ?, summary_json = ? WHERE session_id = ?",
        (now, json.dumps(summary, ensure_ascii=False), session_id),
    )
    conn.commit()
    conn.close()
    # Return the updated doc
    return get_conversation(session_id)


# ---------------------------------------------------------------------------
# Dashboard stats
# ---------------------------------------------------------------------------


def get_dashboard_stats() -> dict:
    """Aggregate stats across all conversations."""
    conn = _connect()

    total = conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
    completed = conn.execute(
        "SELECT COUNT(*) FROM conversations WHERE ended_at IS NOT NULL"
    ).fetchone()[0]

    # Average score from summaries
    avg_score = 0.0
    score_rows = conn.execute(
        "SELECT summary_json FROM conversations WHERE summary_json IS NOT NULL"
    ).fetchall()
    scores = []
    for r in score_rows:
        try:
            s = json.loads(r["summary_json"])
            if "overall_score" in s:
                scores.append(s["overall_score"])
        except (json.JSONDecodeError, KeyError):
            pass
    if scores:
        avg_score = round(sum(scores) / len(scores), 1)

    # Scene breakdown
    scene_rows = conn.execute(
        """
        SELECT c.scene_id,
               COUNT(*) AS cnt,
               AVG(
                 CAST(json_extract(c.summary_json, '$.overall_score') AS REAL)
               ) AS avg_s
        FROM conversations c
        WHERE c.summary_json IS NOT NULL
        GROUP BY c.scene_id
        ORDER BY cnt DESC
        """
    ).fetchall()
    scenes_practiced = [
        {"scene_id": r["scene_id"], "count": r["cnt"], "avg_score": round(r["avg_s"] or 0, 1)}
        for r in scene_rows
    ]

    # Estimated total minutes (30s per user turn)
    turn_count = conn.execute("SELECT COUNT(*) FROM turns WHERE user_text != ''").fetchone()[0]
    total_minutes = round(turn_count * 0.5, 1)

    conn.close()

    return {
        "total_sessions": total,
        "completed_sessions": completed,
        "total_minutes": total_minutes,
        "average_score": avg_score,
        "scenes_practiced": scenes_practiced,
    }


# ---------------------------------------------------------------------------
# Migration: JSON files → SQLite
# ---------------------------------------------------------------------------


def migrate_json_to_sqlite() -> int:
    """
    Import all existing JSON conversation files into SQLite.
    After successful migration, renames conversations/ → conversations_backup/.
    Returns the number of migrated sessions.
    """
    conv_dir = DATA_DIR / "conversations"
    if not conv_dir.exists() or not conv_dir.is_dir():
        return 0

    json_files = sorted(conv_dir.glob("*.json"))
    if not json_files:
        return 0

    init_db()
    count = 0
    for jf in json_files:
        try:
            with open(jf, "r", encoding="utf-8") as f:
                doc = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue

        sid = doc.get("session_id", jf.stem)
        scene_id = doc.get("scene_id", "unknown")
        created_at = doc.get("created_at", datetime.now(timezone.utc).isoformat())
        ended_at = doc.get("ended_at")
        summary_json = json.dumps(doc.get("summary"), ensure_ascii=False) if doc.get("summary") else None

        conn = _connect()
        # Upsert conversation
        existing = conn.execute(
            "SELECT session_id FROM conversations WHERE session_id = ?", (sid,)
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE conversations SET scene_id=?, created_at=?, ended_at=?, summary_json=? WHERE session_id=?",
                (scene_id, created_at, ended_at, summary_json, sid),
            )
        else:
            conn.execute(
                "INSERT INTO conversations (session_id, scene_id, created_at, ended_at, summary_json) VALUES (?,?,?,?,?)",
                (sid, scene_id, created_at, ended_at, summary_json),
            )

        # Insert turns (skip if already present)
        for msg in doc.get("messages", []):
            score = msg.get("pronunciation_score")
            conn.execute(
                """
                INSERT OR IGNORE INTO turns
                  (session_id, turn_number, user_text, corrected_text, ai_text,
                   corrections_json, pronunciation_score, pronunciation_note)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    sid,
                    msg.get("turn", 0),
                    msg.get("user_text", ""),
                    msg.get("corrected_text", ""),
                    msg.get("ai_text", ""),
                    json.dumps(msg.get("corrections", []), ensure_ascii=False),
                    json.dumps(score) if score else None,
                    msg.get("pronunciation_note", ""),
                ),
            )
        conn.commit()
        conn.close()
        count += 1

    # Rename old directory
    backup_dir = DATA_DIR / "conversations_backup"
    if backup_dir.exists():
        import shutil
        shutil.rmtree(str(backup_dir))
    conv_dir.rename(backup_dir)

    return count
