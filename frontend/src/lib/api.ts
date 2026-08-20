import { env } from './env'
import { HttpClient } from './http'
import { supabase } from './supabase'

const http = new HttpClient(env.apiBaseUrl, async () => {
  const { data, error } = await supabase.auth.getSession()
  if (error) throw error
  return data.session?.access_token ?? null
})

export type AuthenticatedUser = { id: string; email: string | null }

export const api = {
  getCurrentUser: () => http.get<AuthenticatedUser>('/auth/me'),
  get: http.get.bind(http),
  post: http.post.bind(http),
  put: http.put.bind(http),
  patch: http.patch.bind(http),
  delete: http.delete.bind(http),
}

export { ApiError } from './http'
export type { RequestOptions } from './http'
