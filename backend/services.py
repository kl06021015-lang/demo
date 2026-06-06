"""
Business logic for the English speaking practice app.
- SceneManager: scene loading
- ConversationManager: conversation persistence (SQLite via database.py)
- ConversationEngine: DeepSeek API for dialogue + corrections + scoring
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
# ConversationEngine  (DeepSeek API via OpenAI SDK)
# ---------------------------------------------------------------------------

CONVERSATION_SYSTEM = """\
You are an English speaking practice partner. You must ALWAYS speak in English — your reply field must be in English. You must respond with ONLY a valid JSON object — no other text, no markdown fences.

Current scenario: {scene_name}
Your role: {role}
Difficulty: {difficulty}
Grammar focus: {grammar_focus}

JSON schema you MUST follow:
{{
  "reply": "Your conversational reply as the character in ENGLISH (1-3 natural English sentences)",
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
- reply: MUST be in English, natural, in-character, appropriate for {difficulty} level
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
    """Handles DeepSeek API calls for dialogue generation and summarisation."""

    def __init__(self, api_key: Optional[str] = None,
                 base_url: Optional[str] = None,
                 model: Optional[str] = None) -> None:
        self._api_key = api_key or os.getenv("DEEPSEEK_API_KEY", "")
        self._base_url = base_url or os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        self._model = model or os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        self._client: Optional[OpenAI] = None

    @property
    def client(self) -> OpenAI:
        if self._client is None:
            if not self._api_key:
                raise RuntimeError("DEEPSEEK_API_KEY not set.")
            self._client = OpenAI(api_key=self._api_key, base_url=self._base_url)
        return self._client

    # ------------------------------------------------------------------
    # Greet
    # ------------------------------------------------------------------

    def greet(self, scene: dict) -> dict:
        """Generate the first greeting for a new conversation."""
        if not self._api_key:
            return self._fallback_greeting(scene)

        try:
            resp = self.client.chat.completions.create(
                model=self._model,
                max_tokens=150,
                messages=[
                    {"role": "system", "content": "You are an English-only speaking practice partner. Always reply in English only, never Chinese. Reply with a short, natural greeting. No JSON."},
                    {"role": "user", "content": (
                        f"You are a {scene['role']}. "
                        f"Greet the user to start an English conversation in this scene: {scene['name']}. "
                        f"Keep it to 1-2 friendly English sentences. Difficulty: {scene['difficulty']}."
                    )},
                ],
            )
            return {"text": resp.choices[0].message.content.strip()}
        except Exception:
            return self._fallback_greeting(scene)

    def _fallback_greeting(self, scene: dict) -> dict:
        greetings = {
            "beginner": f"Hello! Welcome! I'll be your {scene['role']}. Let's practice English!",
            "intermediate": f"Hi there! I'm your {scene['role']} today. Ready to get started?",
        }
        return {"text": greetings.get(scene.get("difficulty", "beginner"), greetings["beginner"])}

    # ------------------------------------------------------------------
    # Chat (non-streaming)
    # ------------------------------------------------------------------

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
            messages = self._build_messages(system, history, user_text)

            resp = self.client.chat.completions.create(
                model=self._model,
                max_tokens=400,
                messages=messages,
            )
            raw = resp.choices[0].message.content.strip()
            return self._parse_json(raw)
        except Exception:
            return self._fallback_chat(scene, user_text)

    def _fallback_chat(self, scene: dict, user_text: str) -> dict:
        return {
            "reply": f"[模拟回复] You said: '{user_text}'. (Configure DEEPSEEK_API_KEY for AI replies)",
            "corrections": [],
            "pronunciation_note": "",
        }

    # ------------------------------------------------------------------
    # Chat (streaming)
    # ------------------------------------------------------------------

    async def chat_stream(self, scene: dict, history: list[dict], user_text: str):
        """Async generator yielding SSE events for streaming AI replies."""
        if not self._api_key:
            fb = self._fallback_chat(scene, user_text)
            yield f"data: {json.dumps({'type': 'text_delta', 'content': fb['reply']})}\n\n"
            yield f"data: {json.dumps({'type': 'corrections', 'data': fb['corrections']})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            return

        try:
            system = CONVERSATION_SYSTEM.format(
                scene_name=scene["name"],
                role=scene["role"],
                difficulty=scene.get("difficulty", "beginner"),
                grammar_focus=", ".join(scene.get("grammar_focus", [])),
            )
            messages = self._build_messages(system, history, user_text)

            full_text = ""
            stream = self.client.chat.completions.create(
                model=self._model,
                max_tokens=400,
                messages=messages,
                stream=True,
            )
            for chunk in stream:
                delta = chunk.choices[0].delta
                if delta.content:
                    full_text += delta.content
                    yield f"data: {json.dumps({'type': 'text_delta', 'content': delta.content})}\n\n"

            parsed = self._parse_json(full_text)
            corrections = parsed.get("corrections", [])
            yield f"data: {json.dumps({'type': 'corrections', 'data': corrections})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception:
            fb = self._fallback_chat(scene, user_text)
            yield f"data: {json.dumps({'type': 'text_delta', 'content': fb['reply']})}\n\n"
            yield f"data: {json.dumps({'type': 'corrections', 'data': fb['corrections']})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

    # ------------------------------------------------------------------
    # Summarize
    # ------------------------------------------------------------------

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
            resp = self.client.chat.completions.create(
                model=self._model,
                max_tokens=800,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": f"Conversation transcript:\n\n{transcript}"},
                ],
            )
            raw = resp.choices[0].message.content.strip()
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
            "suggestions": ["设置有效的 DEEPSEEK_API_KEY 以获取真实 AI 评估"],
            "encouragement": "你今天表现不错！配置有效的 DeepSeek API Key 后可获得详细评估报告。",
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_messages(self, system: str, history: list[dict], user_text: str) -> list[dict]:
        """Build OpenAI-format messages list: system + history + current user text."""
        msgs = [{"role": "system", "content": system}]
        for turn in history[-10:]:
            if turn.get("user_text"):
                msgs.append({"role": "user", "content": turn["user_text"]})
            if turn.get("ai_text"):
                msgs.append({"role": "assistant", "content": turn["ai_text"]})
        msgs.append({"role": "user", "content": user_text})
        return msgs

    def _parse_json(self, raw: str) -> dict:
        """Parse JSON response, with fallback for markdown fences."""
        raw = raw.strip()
        if raw.startswith("```"):
            lines = raw.split("\n")
            raw = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
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
            raise RuntimeError("No OPENAI_API_KEY configured — cannot transcribe audio")

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
        except Exception as e:
            err_msg = str(e)
            if "insufficient_quota" in err_msg.lower() or "429" in err_msg:
                raise RuntimeError("OpenAI Whisper 额度已用完，请前往 platform.openai.com 充值。语音输入暂时不可用，请使用文字输入。")
            elif "invalid" in err_msg.lower() or "401" in err_msg:
                raise RuntimeError("OpenAI API Key 无效，语音输入暂时不可用，请使用文字输入。")
            else:
                raise RuntimeError(f"语音识别失败: {err_msg}")
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
