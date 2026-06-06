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

        CREATE TABLE IF NOT EXISTS goals (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            goal_type       TEXT NOT NULL DEFAULT 'daily',
            target_minutes  INTEGER NOT NULL DEFAULT 10,
            is_active       INTEGER NOT NULL DEFAULT 1,
            created_at      TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS checkins (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            checkin_date     TEXT NOT NULL,
            minutes_practiced INTEGER NOT NULL DEFAULT 0,
            turns_completed  INTEGER NOT NULL DEFAULT 0,
            created_at       TEXT NOT NULL
        );

        CREATE UNIQUE INDEX IF NOT EXISTS idx_checkins_date ON checkins(checkin_date);
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

    # Daily scores for trend chart (last 30 days)
    daily_score_rows = conn.execute(
        """
        SELECT date(ended_at) as day,
               AVG(CAST(json_extract(summary_json, '$.overall_score') AS REAL)) as avg_score,
               COUNT(*) as sessions
        FROM conversations
        WHERE ended_at IS NOT NULL
          AND summary_json IS NOT NULL
          AND ended_at >= date('now', '-30 days')
        GROUP BY day
        ORDER BY day
        """
    ).fetchall()

    conn.close()

    # Streak and check-in data
    streak = get_streak()
    checkins = get_checkin_history(7)  # Last 7 days for weekly progress
    total_checkin_minutes = sum(c["minutes_practiced"] for c in checkins)

    # Badges
    badges: list[dict] = []
    if streak["current_streak"] >= 3:
        badges.append({"id": "streak_3", "name": "连续3天", "icon": "🔥", "description": f"连续打卡 {streak['current_streak']} 天"})
    if streak["current_streak"] >= 7:
        badges.append({"id": "streak_7", "name": "坚持一周", "icon": "⭐", "description": "连续打卡 7 天"})
    if streak["current_streak"] >= 30:
        badges.append({"id": "streak_30", "name": "月度之星", "icon": "🌟", "description": "连续打卡 30 天"})
    if total_minutes >= 30:
        badges.append({"id": "time_30", "name": "初露锋芒", "icon": "⏱️", "description": f"累计练习 {total_minutes} 分钟"})
    if total_minutes >= 100:
        badges.append({"id": "time_100", "name": "持之以恒", "icon": "💪", "description": f"累计练习 {total_minutes} 分钟"})
    if total_minutes >= 500:
        badges.append({"id": "time_500", "name": "英语达人", "icon": "🏆", "description": f"累计练习 {total_minutes} 分钟"})
    if completed >= 5:
        badges.append({"id": "complete_5", "name": "初试牛刀", "icon": "🎯", "description": f"完成 {completed} 次对话"})
    if completed >= 20:
        badges.append({"id": "complete_20", "name": "对话能手", "icon": "💬", "description": f"完成 {completed} 次对话"})
    if avg_score >= 7.5 and completed >= 3:
        badges.append({"id": "quality", "name": "优质表达", "icon": "✨", "description": f"平均评分 {avg_score}"})

    # Active goal
    goal = get_active_goal("daily")
    weekly_goal = get_active_goal("weekly")

    daily_scores = [
        {"date": r["day"], "avg_score": round(r["avg_score"] or 0, 1), "sessions": r["sessions"]}
        for r in daily_score_rows
    ]

    # XP & Level calculation
    # XP = total_minutes * 10 + bonus for high-score sessions
    high_score_count = 0
    for r in score_rows:
        try:
            s = json.loads(r["summary_json"])
            if s.get("overall_score", 0) >= 7:
                high_score_count += 1
        except (json.JSONDecodeError, KeyError):
            pass
    xp = int(total_minutes * 10 + high_score_count * 20)
    import math
    level = int(math.sqrt(xp / 100)) + 1
    xp_for_next = (level) ** 2 * 100  # XP needed for next level

    return {
        "total_sessions": total,
        "completed_sessions": completed,
        "total_minutes": total_minutes,
        "average_score": avg_score,
        "scenes_practiced": scenes_practiced,
        "streak": streak,
        "badges": badges,
        "weekly_checkins": checkins,
        "weekly_minutes": total_checkin_minutes,
        "goal": goal,
        "weekly_goal": weekly_goal,
        "daily_scores": daily_scores,
        "xp": xp,
        "level": level,
        "xp_for_next": xp_for_next,
    }


# ---------------------------------------------------------------------------
# Goals & Check-ins
# ---------------------------------------------------------------------------


def set_goal(goal_type: str, target_minutes: int) -> dict:
    """Deactivate existing goals of the same type, then insert a new active goal."""
    now = datetime.now(timezone.utc).isoformat()
    conn = _connect()
    # Deactivate existing goals of this type
    conn.execute(
        "UPDATE goals SET is_active = 0 WHERE goal_type = ? AND is_active = 1",
        (goal_type,),
    )
    cur = conn.execute(
        "INSERT INTO goals (goal_type, target_minutes, is_active, created_at) VALUES (?, ?, 1, ?)",
        (goal_type, target_minutes, now),
    )
    conn.commit()
    goal_id = cur.lastrowid
    conn.close()
    return {"id": goal_id, "goal_type": goal_type, "target_minutes": target_minutes, "is_active": True, "created_at": now}


def get_active_goal(goal_type: str = "daily") -> dict | None:
    """Return the current active goal of the given type, or None."""
    conn = _connect()
    row = conn.execute(
        "SELECT * FROM goals WHERE goal_type = ? AND is_active = 1 ORDER BY created_at DESC LIMIT 1",
        (goal_type,),
    ).fetchone()
    conn.close()
    if row is None:
        return None
    return {"id": row["id"], "goal_type": row["goal_type"], "target_minutes": row["target_minutes"], "is_active": bool(row["is_active"]), "created_at": row["created_at"]}


def do_checkin(minutes_practiced: int = 0, turns_completed: int = 0) -> dict:
    """Record a check-in for today. Upserts if already checked in today."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    now = datetime.now(timezone.utc).isoformat()
    conn = _connect()

    existing = conn.execute(
        "SELECT * FROM checkins WHERE checkin_date = ?", (today,)
    ).fetchone()

    if existing:
        conn.execute(
            "UPDATE checkins SET minutes_practiced = minutes_practiced + ?, turns_completed = turns_completed + ?, created_at = ? WHERE checkin_date = ?",
            (minutes_practiced, turns_completed, now, today),
        )
    else:
        conn.execute(
            "INSERT INTO checkins (checkin_date, minutes_practiced, turns_completed, created_at) VALUES (?, ?, ?, ?)",
            (today, minutes_practiced, turns_completed, now),
        )
    conn.commit()

    # Return updated row
    row = conn.execute("SELECT * FROM checkins WHERE checkin_date = ?", (today,)).fetchone()
    conn.close()
    return {
        "checkin_date": row["checkin_date"],
        "minutes_practiced": row["minutes_practiced"],
        "turns_completed": row["turns_completed"],
        "created_at": row["created_at"],
    }


def get_checkin_history(days: int = 30) -> list[dict]:
    """Return check-in records for the last N days."""
    conn = _connect()
    rows = conn.execute(
        """
        SELECT * FROM checkins
        WHERE checkin_date >= date('now', ? || ' days')
        ORDER BY checkin_date DESC
        """,
        (f"-{days}",),
    ).fetchall()
    conn.close()
    return [
        {
            "checkin_date": r["checkin_date"],
            "minutes_practiced": r["minutes_practiced"],
            "turns_completed": r["turns_completed"],
        }
        for r in rows
    ]


def get_streak() -> dict:
    """Calculate current streak and longest streak of consecutive check-in days."""
    conn = _connect()
    rows = conn.execute(
        "SELECT checkin_date FROM checkins ORDER BY checkin_date DESC"
    ).fetchall()
    conn.close()

    if not rows:
        return {"current_streak": 0, "longest_streak": 0, "total_checkins": 0}

    dates = sorted({r["checkin_date"] for r in rows})

    # Calculate longest streak
    longest = 0
    current_run = 1
    for i in range(1, len(dates)):
        d1 = dates[i - 1]
        d2 = dates[i]
        # Check if d2 is the day after d1
        from datetime import timedelta as td
        d1_obj = datetime.strptime(d1, "%Y-%m-%d")
        d2_obj = datetime.strptime(d2, "%Y-%m-%d")
        if (d2_obj - d1_obj).days == 1:
            current_run += 1
        else:
            longest = max(longest, current_run)
            current_run = 1
    longest = max(longest, current_run)

    # Calculate current streak (how many consecutive days ending at today/latest)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    latest = dates[-1]
    current_streak = 0
    if latest == today or latest == (datetime.now(timezone.utc) - td(days=1)).strftime("%Y-%m-%d"):
        # Count backwards from latest
        from datetime import timedelta as td2
        streak = 1
        for i in range(len(dates) - 2, -1, -1):
            prev = dates[i + 1]
            curr = dates[i]
            p_obj = datetime.strptime(prev, "%Y-%m-%d")
            c_obj = datetime.strptime(curr, "%Y-%m-%d")
            if (p_obj - c_obj).days == 1:
                streak += 1
            else:
                break
        current_streak = streak

    return {
        "current_streak": current_streak,
        "longest_streak": longest,
        "total_checkins": len(dates),
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
