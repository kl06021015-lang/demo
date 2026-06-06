"""
Business logic for the English speaking practice app.
- SceneManager: scene loading
- ConversationManager: conversation persistence (SQLite via database.py)
- ConversationEngine: Claude API for dialogue + corrections + scoring
- SpeechService: Whisper STT + Edge-TTS
"""

import json
import os
import uuid
import base64
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import anthropic
from openai import OpenAI

from database import (
    create_conversation as db_create_conversation,
    get_conversation as db_get_conversation,
    append_turn as db_append_turn,
    end_conversation as db_end_conversation,
)

# ---------------------------------------------------------------------------
# Data directory helpers
# ---------------------------------------------------------------------------

DATA_DIR = Path(__file__).parent / "data"


def _scene_path() -> Path:
    return DATA_DIR / "scenes.json"


# ---------------------------------------------------------------------------
# SceneManager
# ---------------------------------------------------------------------------

class SceneManager:
    """Load and query preset scenes from scenes.json."""

    def __init__(self) -> None:
        self._scenes: list[dict] = []

    def _load(self) -> list[dict]:
        if self._scenes:
            return self._scenes
        with open(_scene_path(), "r", encoding="utf-8") as f:
            data = json.load(f)
        self._scenes = data["scenes"]
        return self._scenes

    def list_scenes(self) -> list[dict]:
        """Return all scenes (id, name, description, difficulty, icon)."""
        return [
            {
                "id": s["id"],
                "name": s["name"],
                "description": s["description"],
                "difficulty": s["difficulty"],
                "icon": s.get("icon", ""),
                "suggested_vocabulary": s.get("suggested_vocabulary", []),
                "grammar_focus": s.get("grammar_focus", []),
            }
            for s in self._load()
        ]

    def get_scene(self, scene_id: str) -> Optional[dict]:
        """Return full scene dict (including system_prompt) by id."""
        for s in self._load():
            if s["id"] == scene_id:
                return s
        return None


# ---------------------------------------------------------------------------
# ConversationManager
# ---------------------------------------------------------------------------

class ConversationManager:
    """Persist conversation records via SQLite database."""

    def create(self, scene_id: str) -> dict:
        session_id = uuid.uuid4().hex[:12]
        return db_create_conversation(session_id, scene_id)

    def load(self, session_id: str) -> Optional[dict]:
        return db_get_conversation(session_id)

    def append_message(self, session_id: str, turn_data: dict) -> None:
        doc = self.load(session_id)
        if doc is None:
            raise FileNotFoundError(f"Conversation {session_id} not found")
        db_append_turn(session_id, turn_data)

    def end(self, session_id: str) -> dict:
        doc = self.load(session_id)
        if doc is None:
            raise FileNotFoundError(f"Conversation {session_id} not found")
        return doc  # caller is responsible for passing summary to db_end_conversation


# ---------------------------------------------------------------------------
# ConversationEngine  (Claude API)
# ---------------------------------------------------------------------------

CONVERSATION_SYSTEM = """\
You are an English speaking practice partner. You must respond with ONLY a valid JSON object — no other text, no markdown fences.

Current scenario: {scene_name}
Your role: {role}
Difficulty: {difficulty}
Grammar focus: {grammar_focus}

JSON schema you MUST follow:
{{
  "reply": "Your conversational reply as the character (1-3 natural sentences)",
  "corrections": [
    {{
      "original": "exact phrase from user that has an error",
      "corrected": "the correct version",
      "explanation": "brief explanation in Chinese about the correction",
      "type": "grammar|word_choice|politeness|other"
    }}
  ],
  "pronunciation_note": "Brief, encouraging note about pronunciation — leave empty string if no audio"
}}

Rules:
- reply: natural, in-character, appropriate for {difficulty} level
- corrections: point out 0-2 major errors only. Don't nitpick. Empty array if the user's English is fine.
- Be encouraging. The user is a Chinese English learner.
"""

SUMMARY_SYSTEM = """\
You are an English language tutor. Review the conversation below and produce a comprehensive learning report.

Scene: {scene_name}
Focus areas: {grammar_focus}

Respond with ONLY a valid JSON object — no other text, no markdown fences.

JSON schema:
{{
  "overall_score": 7.5,
  "grammar_highlights": [
    {{ "pattern": "e.g. tense mixing", "count": 3, "suggestion": "how to improve", "examples": ["example from conversation"] }}
  ],
  "pronunciation_highlights": [
    {{ "phoneme": "e.g. /θ/", "issue": "substituted with /s/", "practice_words": ["think", "three"] }}
  ],
  "vocabulary_used": ["word1", "word2"],
  "strengths": ["what the student did well"],
  "suggestions": ["actionable improvement tips in Chinese"],
  "encouragement": "warm, specific encouragement in Chinese"
}}
"""


class ConversationEngine:
    """Handles Claude API calls for dialogue generation and summarisation."""

    def __init__(self, api_key: Optional[str] = None) -> None:
        key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
        self._api_key = key
        self._client: Optional[anthropic.Anthropic] = None

    @property
    def client(self) -> anthropic.Anthropic:
        if self._client is None:
            if not self._api_key:
                raise RuntimeError(
                    "ANTHROPIC_API_KEY not set. Set the environment variable or pass api_key."
                )
            self._client = anthropic.Anthropic(api_key=self._api_key)
        return self._client

    def greet(self, scene: dict) -> dict:
        """Generate the first greeting for a new conversation."""
        if not self._api_key:
            return self._fallback_greeting(scene)

        try:
            prompt = (
                f"You are a {scene['role']}. "
                f"Greet the user to start a conversation in this scene: {scene['name']}. "
                f"Keep it to 1-2 friendly sentences. Difficulty: {scene['difficulty']}."
            )
            resp = self.client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=150,
                system="Reply with a short, natural greeting only. No JSON.",
                messages=[{"role": "user", "content": prompt}],
            )
            return {"text": resp.content[0].text.strip()}
        except Exception:
            return self._fallback_greeting(scene)

    def _fallback_greeting(self, scene: dict) -> dict:
        greetings = {
            "beginner": f"Hello! Welcome! I'll be your {scene['role']}. Let's practice English!",
            "intermediate": f"Hi there! I'm your {scene['role']} today. Ready to get started?",
        }
        return {"text": greetings.get(scene.get("difficulty", "beginner"), greetings["beginner"])}

    def chat(self, scene: dict, history: list[dict], user_text: str) -> dict:
        """Generate AI reply + corrections + pronunciation note."""
        if not self._api_key:
            return self._fallback_chat(scene, user_text)

        try:
            system = CONVERSATION_SYSTEM.format(
                scene_name=scene["name"],
                role=scene["role"],
                difficulty=scene.get("difficulty", "beginner"),
                grammar_focus=", ".join(scene.get("grammar_focus", [])),
            )
            messages = self._build_history(history, user_text)

            resp = self.client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=400,
                system=system,
                messages=messages,
            )
            raw = resp.content[0].text.strip()
            return self._parse_json(raw)
        except Exception:
            return self._fallback_chat(scene, user_text)

    def _fallback_chat(self, scene: dict, user_text: str) -> dict:
        return {
            "reply": f"[模拟回复] You said: '{user_text}'. In a real setup with Claude API, I would respond naturally as a {scene['role']}.",
            "corrections": [],
            "pronunciation_note": "",
        }

    def summarize(self, scene: dict, messages: list[dict]) -> dict:
        """Generate a summary report for the completed conversation."""
        if not self._api_key:
            return self._fallback_summary()

        try:
            system = SUMMARY_SYSTEM.format(
                scene_name=scene["name"],
                grammar_focus=", ".join(scene.get("grammar_focus", [])),
            )
            transcript = "\n".join(
                f"User: {m.get('user_text', '')}\nAI: {m.get('ai_text', '')}"
                for m in messages
            )
            resp = self.client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=800,
                system=system,
                messages=[{"role": "user", "content": f"Conversation transcript:\n\n{transcript}"}],
            )
            raw = resp.content[0].text.strip()
            return self._parse_json(raw)
        except Exception:
            return self._fallback_summary()

    def _fallback_summary(self) -> dict:
        return {
            "overall_score": 7.5,
            "grammar_highlights": [],
            "pronunciation_highlights": [],
            "vocabulary_used": [],
            "strengths": ["Good effort! (API unavailable — this is a placeholder summary)"],
            "suggestions": ["设置有效的 ANTHROPIC_API_KEY 以获取真实 AI 评估"],
            "encouragement": "你今天表现不错！配置有效的 Claude API Key 后可获得详细评估报告。",
        }

    # ------------------------------------------------------------------
    def _build_history(self, history: list[dict], user_text: str) -> list[dict]:
        """Build Claude messages list from stored conversation history."""
        msgs = []
        # Include last 10 turns for context
        for turn in history[-10:]:
            if turn.get("user_text"):
                msgs.append({"role": "user", "content": turn["user_text"]})
            if turn.get("ai_text"):
                msgs.append({"role": "assistant", "content": turn["ai_text"]})
        msgs.append({"role": "user", "content": user_text})
        return msgs

    def _parse_json(self, raw: str) -> dict:
        """Parse Claude's JSON response, with fallback for markdown fences."""
        raw = raw.strip()
        if raw.startswith("```"):
            # Strip markdown code fences
            lines = raw.split("\n")
            raw = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            # Fallback: treat entire response as plain reply
            return {
                "reply": raw,
                "corrections": [],
                "pronunciation_note": "",
            }


# ---------------------------------------------------------------------------
# SpeechService  (Whisper STT + Edge-TTS)
# ---------------------------------------------------------------------------

class SpeechService:
    """Speech-to-text via OpenAI Whisper; text-to-speech via Edge-TTS."""

    def __init__(self, openai_api_key: Optional[str] = None) -> None:
        key = openai_api_key or os.getenv("OPENAI_API_KEY", "")
        self._api_key = key
        self._client: Optional[OpenAI] = None

    @property
    def client(self) -> OpenAI:
        if self._client is None:
            if not self._api_key:
                raise RuntimeError(
                    "OPENAI_API_KEY not set. Set the environment variable or pass api_key."
                )
            self._client = OpenAI(api_key=self._api_key)
        return self._client

    async def transcribe(self, audio_bytes: bytes, filename: str = "audio.webm") -> str:
        """Transcribe audio bytes to text using Whisper API."""
        if not self._api_key:
            return "[No OPENAI_API_KEY configured — cannot transcribe audio]"

        suffix = Path(filename).suffix or ".webm"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        try:
            with open(tmp_path, "rb") as f:
                resp = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=(filename, f),
                    language="en",
                )
            return resp.text.strip()
        finally:
            os.unlink(tmp_path)

    async def synthesize(self, text: str, voice: str = "en-US-JennyNeural") -> bytes:
        """Convert text to speech MP3 bytes using Edge-TTS."""
        import edge_tts

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(tmp_path)
            with open(tmp_path, "rb") as f:
                return f.read()
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
