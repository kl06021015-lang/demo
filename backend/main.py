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
import base64
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

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
    list_conversations,
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
    print(f"[startup] Migrated {migrated} JSON conversations to SQLite")

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
    if audio is not None and audio.filename:
        audio_bytes = await audio.read()
        user_text = await speech.transcribe(audio_bytes, audio.filename or "audio.webm")
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
    }
    convs.append_message(session_id, turn_data)

    # --- Build response ---
    response = {
        "user_text": user_text,
        "corrected_text": "",
        "ai_reply": {"text": ai_text, "audio_base64": audio_base64},
        "corrections": corrections,
        "pronunciation_score": pronunciation_score,
    }

    # Fill corrected_text from corrections
    if corrections:
        corrected = user_text
        for c in corrections:
            corrected = corrected.replace(c.get("original", ""), c.get("corrected", ""))
        response["corrected_text"] = corrected

    return response


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

    return {
        "session_id": session_id,
        "duration_minutes": _calc_duration(messages),
        "total_turns": len([m for m in messages if m.get("user_text")]),
        "summary": summary,
    }


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
