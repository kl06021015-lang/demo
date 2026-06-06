/**
 * API layer — all backend communication in one file.
 */

const BASE = '/api'

export interface Scene {
  id: string
  name: string
  description: string
  difficulty: string
  icon: string
  suggested_vocabulary: string[]
  grammar_focus: string[]
}

export interface Greeting {
  text: string
}

export interface ConversationCreated {
  session_id: string
  scene: { id: string; name: string; difficulty: string }
  greeting: Greeting
  created_at: string
}

export interface Correction {
  original: string
  corrected: string
  explanation: string
  type: string
}

export interface PronunciationScore {
  overall: number
  note: string
}

export interface MessageResponse {
  user_text: string
  corrected_text: string
  ai_reply: { text: string; audio_base64: string }
  corrections: Correction[]
  pronunciation_score: PronunciationScore | null
}

export interface TurnData {
  turn: number
  user_text: string
  corrected_text: string
  ai_text: string
  corrections: Correction[]
  pronunciation_score: PronunciationScore | null
  pronunciation_note: string
}

export interface ConversationRecord {
  session_id: string
  scene_id: string
  created_at: string
  ended_at: string | null
  messages: TurnData[]
}

export interface GrammarHighlight {
  pattern: string
  count: number
  suggestion: string
  examples: string[]
}

export interface PronunciationHighlight {
  phoneme: string
  issue: string
  practice_words: string[]
}

export interface SummaryData {
  overall_score: number
  grammar_highlights: GrammarHighlight[]
  pronunciation_highlights: PronunciationHighlight[]
  vocabulary_used: string[]
  strengths: string[]
  suggestions: string[]
  encouragement: string
}

export interface ConversationSummary {
  session_id: string
  duration_minutes: number
  total_turns: number
  summary: SummaryData
}

// ---------------------------------------------------------------------------

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const resp = await fetch(`${BASE}${url}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  })
  if (!resp.ok) {
    const err = await resp.text()
    throw new Error(`API Error ${resp.status}: ${err}`)
  }
  return resp.json()
}

// ---------------------------------------------------------------------------
// Public API functions
// ---------------------------------------------------------------------------

export function getScenes(): Promise<{ scenes: Scene[] }> {
  return request('/scenes')
}

export function createConversation(sceneId: string): Promise<ConversationCreated> {
  return request('/conversations', {
    method: 'POST',
    body: JSON.stringify({ scene_id: sceneId }),
  })
}

export function getConversation(sessionId: string): Promise<ConversationRecord> {
  return request(`/conversations/${sessionId}`)
}

export async function sendMessage(
  sessionId: string,
  opts: { text?: string; audio?: Blob; filename?: string }
): Promise<MessageResponse> {
  const form = new FormData()
  if (opts.text) {
    form.append('text', opts.text)
  }
  if (opts.audio) {
    form.append('audio', opts.audio, opts.filename || 'recording.webm')
  }
  const resp = await fetch(`${BASE}/conversations/${sessionId}/message`, {
    method: 'POST',
    body: form,
  })
  if (!resp.ok) {
    const err = await resp.text()
    throw new Error(`API Error ${resp.status}: ${err}`)
  }
  return resp.json()
}

export function endConversation(sessionId: string): Promise<ConversationSummary> {
  return request(`/conversations/${sessionId}/end`, { method: 'POST' })
}
