import { env } from './env'
import { HttpClient } from './http'
import { clearLocalSession, getAccessToken } from './supabase'

const http = new HttpClient(env.apiBaseUrl, getAccessToken, clearLocalSession)

export type AuthenticatedUser = { id: string; email: string | null }
export type ChatThread = {
  id: string
  title: string
  created_at: string
  updated_at: string
}

export type StoredChatMessage = {
  id: string
  role: 'user' | 'assistant' | 'system'
  parts: Array<Record<string, unknown>>
  sequence: number
  created_at: string
}

export const api = {
  getCurrentUser: () => http.get<AuthenticatedUser>('/auth/me'),
  listThreads: () => http.get<ChatThread[]>('/chat/threads'),
  createThread: (title: string) =>
    http.post<ChatThread>('/chat/threads', { title }),
  renameThread: (threadId: string, title: string) =>
    http.patch<ChatThread>(`/chat/threads/${threadId}`, { title }),
  getMessages: (threadId: string) =>
    http.get<StoredChatMessage[]>(`/chat/threads/${threadId}/messages`),
  get: http.get.bind(http),
  post: http.post.bind(http),
  put: http.put.bind(http),
  patch: http.patch.bind(http),
  delete: http.delete.bind(http),
}

export { ApiError } from './http'
export type { RequestOptions } from './http'
