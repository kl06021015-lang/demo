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
  summary?: SummaryData
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

export interface SceneStats {
  scene_id: string
  count: number
  avg_score: number
}

export interface DashboardData {
  total_sessions: number
  completed_sessions: number
  total_minutes: number
  average_score: number
  scenes_practiced: SceneStats[]
}

export interface ConversationSummary {
  session_id: string
  duration_minutes: number
  total_turns: number
  summary: SummaryData
}

export interface ConversationListItem {
  session_id: string
  scene_id: string
  scene_name: string
  created_at: string
  ended_at: string | null
  has_summary: boolean
  turn_count: number
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

export function getDashboard(): Promise<DashboardData> {
  return request('/dashboard')
}

export function getConversationList(limit: number = 20): Promise<{ conversations: ConversationListItem[] }> {
  return request(`/conversations?limit=${limit}`)
}

export async function* sendMessageStream(
  sessionId: string,
  opts: { text?: string; audio?: Blob; filename?: string }
): AsyncGenerator<{ type: string; content?: string; data?: any }> {
  const form = new FormData()
  if (opts.text) form.append('text', opts.text)
  if (opts.audio) form.append('audio', opts.audio, opts.filename || 'recording.webm')

  const resp = await fetch(`${BASE}/conversations/${sessionId}/message/stream`, {
    method: 'POST',
    body: form,
  })
  if (!resp.ok) {
    const err = await resp.text()
    throw new Error(`API Error ${resp.status}: ${err}`)
  }

  const reader = resp.body!.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          yield JSON.parse(line.slice(6))
        } catch { /* skip malformed */ }
      }
    }
  }
}

export function endConversation(sessionId: string): Promise<ConversationSummary> {
  return request(`/conversations/${sessionId}/end`, { method: 'POST' })
}

export function deleteConversation(sessionId: string): Promise<{ ok: boolean }> {
  return request(`/conversations/${sessionId}`, { method: 'DELETE' })
}

// ---------------------------------------------------------------------------
// Vocabulary
// ---------------------------------------------------------------------------

export interface VocabWord {
  id: number
  word: string
  meaning: string
  context: string
  added_at: string
  mastered: number
}

export interface VocabStats {
  total: number
  mastered: number
  learning: number
}

export function getVocabulary(limit = 100, mastered?: boolean): Promise<{ words: VocabWord[]; stats: VocabStats }> {
  const params = new URLSearchParams({ limit: String(limit) })
  if (mastered !== undefined) params.set('mastered', String(mastered))
  return request(`/vocabulary?${params}`)
}

export function addVocabulary(word: string, meaning?: string, context?: string): Promise<VocabWord> {
  return request('/vocabulary', {
    method: 'POST',
    body: JSON.stringify({ word, meaning, context }),
  })
}

export function toggleWordMastered(wordId: number): Promise<VocabWord> {
  return request(`/vocabulary/${wordId}/toggle`, { method: 'POST' })
}

export function deleteVocabulary(wordId: number): Promise<{ ok: boolean }> {
  return request(`/vocabulary/${wordId}`, { method: 'DELETE' })
}
