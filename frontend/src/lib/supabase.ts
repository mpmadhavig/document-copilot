import { createClient } from '@supabase/supabase-js'

import { env } from './env'

export const supabase = createClient(env.supabaseUrl, env.supabaseAnonKey)

export async function getAccessToken(): Promise<string | null> {
  const { data, error } = await supabase.auth.getSession()
  if (error) throw error
  return data.session?.access_token ?? null
}

export async function clearLocalSession(): Promise<void> {
  await supabase.auth.signOut({ scope: 'local' })
}
