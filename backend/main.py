"""
FastAPI application — English Speaking Practice
Single-file API server with all routes.

API keys are read from the .env file.
Copy .env.example to .env and fill in your keys.
"""

from dotenv import load_dotenv
load_dotenv()

import os
import json
import time
import logging
import base64
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, UploadFile, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response, HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "app.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("english-practice")

# ---------------------------------------------------------------------------
# In-memory rate limiter (per IP, no Redis dependency)
# ---------------------------------------------------------------------------
RATE_LIMIT_MAX = int(os.getenv("RATE_LIMIT_MAX", "60"))       # requests
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "60")) # seconds
_rate_buckets: dict[str, list[float]] = {}

def _check_rate_limit(client_ip: str) -> bool:
    """Return True if the request is allowed, False if rate-limited."""
    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW
    bucket = _rate_buckets.get(client_ip, [])
    bucket = [t for t in bucket if t > window_start]  # prune old timestamps
    if len(bucket) >= RATE_LIMIT_MAX:
        _rate_buckets[client_ip] = bucket
        return False
    bucket.append(now)
    _rate_buckets[client_ip] = bucket
    return True

from services import (
    SceneManager,
    ConversationManager,
    ConversationEngine,
    SpeechService,
    DATA_DIR,
)
from database import (
    init_db,
    migrate_json_to_sqlite,
    end_conversation as db_end_conversation,
    delete_conversation as db_delete_conversation,
    list_conversations,
    get_dashboard_stats,
    set_goal,
    get_active_goal,
    do_checkin,
    get_checkin_history,
    get_streak,
)

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = FastAPI(title="English Speaking Practice API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Rate-limit requests per IP. Skips static files and GET requests."""
    if request.method != "GET" and request.url.path.startswith("/api/"):
        client_ip = request.client.host if request.client else "127.0.0.1"
        if not _check_rate_limit(client_ip):
            logger.warning("Rate limit exceeded for %s — %s %s", client_ip, request.method, request.url.path)
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please slow down.", "retry_after": RATE_LIMIT_WINDOW},
            )
    response = await call_next(request)
    return response

# Services
scenes = SceneManager()
convs = ConversationManager()
engine = ConversationEngine()
speech = SpeechService()

# Ensure data directory exists and database is initialized
DATA_DIR.mkdir(parents=True, exist_ok=True)
init_db()
migrated = migrate_json_to_sqlite()
if migrated:
    logger.info("Migrated %d JSON conversations to SQLite", migrated)

logger.info("App started — DEEPSEEK_API_KEY=%s", "set" if os.getenv("DEEPSEEK_API_KEY") else "NOT SET")

# ---------------------------------------------------------------------------
# Routes — Scenes
# ---------------------------------------------------------------------------

@app.get("/api/scenes")
def list_scenes():
    """Return all available practice scenes."""
    return {"scenes": scenes.list_scenes()}


# ---------------------------------------------------------------------------
# Routes — Conversations
# ---------------------------------------------------------------------------

@app.get("/api/dashboard")
def dashboard():
    """Return aggregated learning statistics."""
    return get_dashboard_stats()


@app.get("/api/conversations")
def list_conversation_list(limit: int = 20):
    """Return a list of recent conversations (history)."""
    items = list_conversations(limit)
    # Look up scene names
    for item in items:
        scene = scenes.get_scene(item["scene_id"])
        item["scene_name"] = scene["name"] if scene else item["scene_id"]
    return {"conversations": items}


@app.post("/api/conversations")
def create_conversation(payload: dict):
    """Start a new conversation for a given scene."""
    scene_id = payload.get("scene_id", "")
    scene = scenes.get_scene(scene_id)
    if scene is None:
        raise HTTPException(status_code=404, detail=f"Scene '{scene_id}' not found")

    doc = convs.create(scene_id)
    greeting = engine.greet(scene)

    # Store the greeting as the first AI message
    convs.append_message(doc["session_id"], {
        "turn": 0,
        "user_text": "",
        "ai_text": greeting["text"],
        "corrections": [],
        "pronunciation_score": None,
    })

    return {
        "session_id": doc["session_id"],
        "scene": {
            "id": scene["id"],
            "name": scene["name"],
            "difficulty": scene.get("difficulty", "beginner"),
        },
        "greeting": greeting,
        "created_at": doc["created_at"],
    }


@app.get("/api/conversations/{session_id}")
def get_conversation(session_id: str):
    """Return full conversation record."""
    doc = convs.load(session_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return doc


@app.delete("/api/conversations/{session_id}")
def delete_conversation(session_id: str):
    """Delete a conversation and all its turns."""
    deleted = db_delete_conversation(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"ok": True, "session_id": session_id}


@app.post("/api/conversations/{session_id}/message")
async def send_message(
    session_id: str,
    text: Optional[str] = Form(None),
    audio: Optional[UploadFile] = File(None),
):
    """Process a user message (text or voice) and return AI reply + corrections."""
    doc = convs.load(session_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    scene = scenes.get_scene(doc["scene_id"])
    if scene is None:
        raise HTTPException(status_code=500, detail="Scene not found")

    # --- Resolve user text ---
    user_text = ""
    audio_path = ""  # relative path for DB storage
    if audio is not None and audio.filename:
        try:
            audio_bytes = await audio.read()
            user_text = await speech.transcribe(audio_bytes, audio.filename or "audio.webm")

            # Save audio to disk for persistence
            from database import DATA_DIR as DB_DATA_DIR
            audio_dir = DB_DATA_DIR / "audio" / session_id
            audio_dir.mkdir(parents=True, exist_ok=True)
            turn_num = len(doc.get("messages", []))
            audio_filename = f"turn_{turn_num:03d}.wav"
            (audio_dir / audio_filename).write_bytes(audio_bytes)
            audio_path = audio_filename
        except RuntimeError as e:
            logger.error("Speech recognition failed: %s", e)
            raise HTTPException(status_code=400, detail=str(e))
    elif text:
        user_text = text.strip()
    else:
        raise HTTPException(status_code=400, detail="Provide 'text' or 'audio'")

    if not user_text:
        raise HTTPException(status_code=400, detail="Empty input")

    # --- Call Claude ---
    result = engine.chat(scene, doc.get("messages", []), user_text)
    ai_text = result.get("reply", "")
    corrections = result.get("corrections", [])
    pronunciation_note = result.get("pronunciation_note", "")

    # --- Generate TTS audio for AI reply ---
    audio_base64 = ""
    try:
        mp3_bytes = await speech.synthesize(ai_text)
        audio_base64 = base64.b64encode(mp3_bytes).decode("utf-8")
    except Exception:
        # TTS failure is non-fatal — continue without audio
        pass

    # --- Build pronunciation score ---
    pronunciation_score = None
    if audio is not None and audio.filename:
        # Score based on Claude's corrections count as a fluency proxy
        corr_count = len(result.get("corrections", []))
        if corr_count == 0:
            overall = 8.5
        elif corr_count == 1:
            overall = 7.0
        else:
            overall = max(5.0, 7.5 - corr_count * 1.5)
        pronunciation_score = {
            "overall": round(overall, 1),
            "note": pronunciation_note or ("Good pronunciation!" if overall >= 8 else "Keep practicing!"),
        }

    # --- Store turn ---
    turn = len(doc.get("messages", []))
    turn_data = {
        "turn": turn,
        "user_text": user_text,
        "corrected_text": "",  # Will be filled if there are corrections
        "ai_text": ai_text,
        "corrections": corrections,
        "pronunciation_score": pronunciation_score,
        "pronunciation_note": pronunciation_note,
        "audio_path": audio_path,
    }
    convs.append_message(session_id, turn_data)

    # --- Build response ---
    response = {
        "user_text": user_text,
        "corrected_text": "",
        "ai_reply": {"text": ai_text, "audio_base64": audio_base64},
        "corrections": corrections,
        "pronunciation_score": pronunciation_score,
        "audio_url": f"/api/audio/{session_id}/{audio_path}" if audio_path else None,
    }

    # Fill corrected_text from corrections
    if corrections:
        corrected = user_text
        for c in corrections:
            corrected = corrected.replace(c.get("original", ""), c.get("corrected", ""))
        response["corrected_text"] = corrected

    return response


@app.post("/api/conversations/{session_id}/message/stream")
async def send_message_stream(
    session_id: str,
    text: Optional[str] = Form(None),
    audio: Optional[UploadFile] = File(None),
):
    """Stream AI reply via Server-Sent Events."""
    doc = convs.load(session_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    scene = scenes.get_scene(doc["scene_id"])
    if scene is None:
        raise HTTPException(status_code=500, detail="Scene not found")

    # Resolve user text
    user_text = ""
    audio_path = ""
    if audio is not None and audio.filename:
        try:
            audio_bytes = await audio.read()
            user_text = await speech.transcribe(audio_bytes, audio.filename or "audio.webm")
            # Save audio to disk
            from database import DATA_DIR as DB_DATA_DIR
            audio_dir = DB_DATA_DIR / "audio" / session_id
            audio_dir.mkdir(parents=True, exist_ok=True)
            turn_num = len(doc.get("messages", []))
            audio_filename = f"turn_{turn_num:03d}.wav"
            (audio_dir / audio_filename).write_bytes(audio_bytes)
            audio_path = audio_filename
        except RuntimeError as e:
            logger.error("Speech recognition failed: %s", e)
            raise HTTPException(status_code=400, detail=str(e))
    elif text:
        user_text = text.strip()
    else:
        raise HTTPException(status_code=400, detail="Provide 'text' or 'audio'")

    if not user_text:
        raise HTTPException(status_code=400, detail="Empty input")

    async def event_stream():
        accumulated_text = ""
        corrections_data = []
        async for sse_event in engine.chat_stream(scene, doc.get("messages", []), user_text):
            # Parse the SSE event to extract data for DB storage
            if sse_event.startswith("data: "):
                try:
                    data = json.loads(sse_event[6:].strip())  # strip "data: " prefix
                    etype = data.get("type", "")
                    if etype == "text_delta":
                        accumulated_text += data.get("content", "")
                    elif etype == "corrections":
                        corrections_data = data.get("data", [])
                except json.JSONDecodeError:
                    pass
            yield sse_event

        # After stream, compute pronunciation score and store the turn
        pronunciation_score = None
        pronunciation_note = ""
        if audio is not None and audio.filename:
            corr_count = len(corrections_data)
            if corr_count == 0:
                overall = 8.5
            elif corr_count == 1:
                overall = 7.0
            else:
                overall = max(5.0, 7.5 - corr_count * 1.5)
            pronunciation_score = {
                "overall": round(overall, 1),
                "note": "Good pronunciation!" if overall >= 8 else "Keep practicing!",
            }
            pronunciation_note = pronunciation_score["note"]

        turn = len(doc.get("messages", []))
        convs.append_message(session_id, {
            "turn": turn,
            "user_text": user_text,
            "corrected_text": "",
            "ai_text": accumulated_text,
            "corrections": corrections_data,
            "pronunciation_score": pronunciation_score,
            "pronunciation_note": pronunciation_note,
            "audio_path": audio_path,
        })

        # Generate and send audio
        try:
            mp3_bytes = await speech.synthesize(accumulated_text)
            audio_b64 = base64.b64encode(mp3_bytes).decode("utf-8")
            yield f"data: {json.dumps({'type': 'audio', 'data': audio_b64})}\n\n"
        except Exception:
            pass

        # Notify frontend of the persisted audio_url
        if audio_path:
            yield f"data: {json.dumps({'type': 'audio_url', 'data': f'/api/audio/{session_id}/{audio_path}'})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/conversations/{session_id}/end")
def end_conversation(session_id: str):
    """End the conversation and generate a learning summary."""
    doc = convs.load(session_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Prevent duplicate calls: if already ended, return existing summary
    if doc.get("ended_at"):
        return {
            "session_id": session_id,
            "duration_minutes": _calc_duration(doc.get("messages", [])),
            "total_turns": len([m for m in doc.get("messages", []) if m.get("user_text")]),
            "summary": doc.get("summary", {}),
            "message": "Conversation already ended",
        }

    scene = scenes.get_scene(doc["scene_id"])
    if scene is None:
        raise HTTPException(status_code=500, detail="Scene not found")

    messages = doc.get("messages", [])

    # Generate summary via Claude
    try:
        summary = engine.summarize(scene, messages)
    except Exception as e:
        summary = {
            "overall_score": 0,
            "grammar_highlights": [],
            "pronunciation_highlights": [],
            "vocabulary_used": [],
            "strengths": [],
            "suggestions": [f"Summary generation failed: {str(e)}"],
            "encouragement": "Great effort today! Keep practicing!",
        }

    # Mark ended and persist summary
    doc = db_end_conversation(session_id, summary)

    # Auto check-in when conversation ends
    duration = _calc_duration(messages)
    turns = len([m for m in messages if m.get("user_text")])
    try:
        do_checkin(minutes_practiced=int(duration), turns_completed=turns)
    except Exception:
        pass  # Check-in failure is non-fatal

    return {
        "session_id": session_id,
        "duration_minutes": duration,
        "total_turns": turns,
        "summary": summary,
    }


@app.get("/api/conversations/{session_id}/export")
def export_report(session_id: str):
    """Generate a standalone HTML learning report."""
    doc = convs.load(session_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if not doc.get("summary"):
        raise HTTPException(status_code=400, detail="Conversation has no summary yet. End the conversation first.")

    scene = scenes.get_scene(doc["scene_id"])
    scene_name = scene["name"] if scene else doc["scene_id"]
    s = doc["summary"]

    score = s.get("overall_score", 0)
    score_pct = round(score * 10)

    def _sc(c: str) -> str:
        """Score color helper."""
        if score >= 8:
            return "#18a058"
        if score >= 6:
            return "#f0a020"
        return "#d03050"

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>英语练习报告 — {scene_name}</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width:720px; margin:0 auto; padding:32px 16px; color:#333; background:#fff }}
h1 {{ text-align:center; font-size:22px; margin-bottom:8px; color:#2080f0 }}
.meta {{ text-align:center; font-size:13px; color:#999; margin-bottom:24px }}
.score-circle {{ width:140px; height:140px; border-radius:50%; margin:0 auto 24px; display:flex; align-items:center; justify-content:center; flex-direction:column; border:8px solid {_sc(score)}; background:#f9f9f9 }}
.score-num {{ font-size:40px; font-weight:700; color:{_sc(score)} }}
.score-label {{ font-size:12px; color:#999; margin-top:4px }}
.section {{ margin-bottom:20px; padding:16px; border-radius:8px; background:#fafafa; border-left:4px solid #2080f0 }}
.section h3 {{ font-size:15px; margin-bottom:8px; color:#333 }}
.section li {{ font-size:13px; line-height:1.7; margin-bottom:4px; color:#555 }}
.tag {{ display:inline-block; padding:2px 8px; border-radius:4px; font-size:11px; margin:2px 4px 2px 0 }}
.tag-er {{ background:#ffeaea; color:#d03050 }}
.tag-ok {{ background:#e8f5e9; color:#18a058 }}
.tag-warn {{ background:#fff3e0; color:#f0a020 }}
.footer {{ text-align:center; margin-top:32px; padding-top:16px; border-top:1px solid #eee; font-size:12px; color:#ccc }}
@media print {{ body {{ padding:16px }} .section {{ break-inside:avoid }} }}
</style>
</head>
<body>

<h1>📊 课后总结</h1>
<div class="meta">
  场景：{scene_name} &nbsp;|&nbsp;
  词汇：{len(s.get("vocabulary_used", []))} 个 &nbsp;|&nbsp;
  对话轮数：{len([m for m in doc.get("messages", []) if m.get("user_text")])}
</div>

<div class="score-circle">
  <div class="score-num">{score}</div>
  <div class="score-label">综合评分</div>
</div>
"""
    # Strengths
    if s.get("strengths"):
        html += '<div class="section"><h3>✅ 表现亮点</h3><ul>'
        for x in s["strengths"]:
            html += f"<li>{x}</li>"
        html += '</ul></div>'

    # Grammar
    if s.get("grammar_highlights"):
        html += '<div class="section"><h3>📝 语法薄弱点</h3>'
        for g in s["grammar_highlights"]:
            html += f'<div style="margin-bottom:8px"><span class="tag tag-er">{g.get("count",0)}次</span> <strong>{g.get("pattern","")}</strong>'
            html += f'<div style="font-size:12px;color:#888;margin:2px 0">{g.get("suggestion","")}</div>'
            for ex in g.get("examples", []):
                html += f'<span class="tag tag-warn">\"{ex}\"</span>'
            html += '</div>'
        html += '</div>'

    # Pronunciation
    if s.get("pronunciation_highlights"):
        html += '<div class="section"><h3>🔊 发音重点</h3>'
        for p in s["pronunciation_highlights"]:
            html += f'<div style="margin-bottom:8px"><strong>音素 {p.get("phoneme","")}</strong> — {p.get("issue","")}'
            for w in p.get("practice_words", []):
                html += f'<span class="tag tag-ok">练习：{w}</span>'
            html += '</div>'
        html += '</div>'

    # Suggestions
    if s.get("suggestions"):
        html += '<div class="section"><h3>💡 改进建议</h3><ul>'
        for x in s["suggestions"]:
            html += f"<li>{x}</li>"
        html += '</ul></div>'

    # Encouragement
    if s.get("encouragement"):
        html += f'<div style="text-align:center;padding:20px;background:#f0f9ff;border-radius:8px;font-size:16px;color:#2080f0">{s["encouragement"]}</div>'

    html += '<div class="footer">Generated by AI 英语口语练习 · English Speaking Practice</div></body></html>'

    return HTMLResponse(content=html, headers={
        "Content-Disposition": f"attachment; filename=english-practice-report-{session_id}.html"
    })


# ---------------------------------------------------------------------------
# Routes — Audio playback
# ---------------------------------------------------------------------------


@app.get("/api/audio/{session_id}/{filename}")
def serve_audio(session_id: str, filename: str):
    """Serve a saved user voice recording."""
    from database import DATA_DIR as DB_DATA_DIR
    audio_path = DB_DATA_DIR / "audio" / session_id / filename
    if not audio_path.exists() or not audio_path.is_file():
        raise HTTPException(status_code=404, detail="Audio recording not found")
    return FileResponse(
        path=str(audio_path),
        media_type="audio/wav",
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )


# ---------------------------------------------------------------------------
# Routes — Goals & Check-ins
# ---------------------------------------------------------------------------


@app.get("/api/goals")
def get_goals():
    """Return active daily and weekly goals, plus current streak."""
    daily = get_active_goal("daily")
    weekly = get_active_goal("weekly")
    streak = get_streak()
    return {
        "daily_goal": daily,
        "weekly_goal": weekly,
        "streak": streak,
    }


@app.post("/api/goals")
def create_or_update_goal(payload: dict):
    """Set a new learning goal. Deactivates previous goal of same type."""
    goal_type = payload.get("goal_type", "daily")
    target_minutes = payload.get("target_minutes", 10)

    if goal_type not in ("daily", "weekly"):
        raise HTTPException(status_code=400, detail="goal_type must be 'daily' or 'weekly'")
    if not isinstance(target_minutes, int) or target_minutes < 1 or target_minutes > 600:
        raise HTTPException(status_code=400, detail="target_minutes must be an integer between 1 and 600")

    goal = set_goal(goal_type, target_minutes)
    return {"goal": goal}


@app.post("/api/checkins")
def create_checkin(payload: Optional[dict] = None):
    """Record a manual check-in for today (upserts)."""
    minutes = (payload or {}).get("minutes_practiced", 0)
    turns = (payload or {}).get("turns_completed", 0)
    checkin = do_checkin(minutes_practiced=minutes, turns_completed=turns)
    streak = get_streak()
    return {"checkin": checkin, "streak": streak}


@app.get("/api/checkins")
def list_checkins(days: int = 30):
    """Return check-in history for the specified number of days."""
    if days < 1 or days > 365:
        days = 30
    history = get_checkin_history(days)
    streak = get_streak()
    return {"checkins": history, "streak": streak}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _calc_duration(messages: list[dict]) -> float:
    """Estimate conversation duration in minutes (approx 30s per turn)."""
    turns = len([m for m in messages if m.get("user_text")])
    return round(turns * 0.5, 1)


# ---------------------------------------------------------------------------
# Static files (production fallback)
# ---------------------------------------------------------------------------
frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
