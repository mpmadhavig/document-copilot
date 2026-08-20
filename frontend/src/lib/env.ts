function required(name: string, value: string | undefined): string {
  const normalized = value?.trim()
  if (!normalized) {
    throw new Error(`Missing required environment variable: ${name}`)
  }
  return normalized
}

function httpUrl(name: string, value: string | undefined): string {
  const rawValue = required(name, value)

  try {
    const url = new URL(rawValue)
    if (url.protocol !== 'http:' && url.protocol !== 'https:') {
      throw new Error('unsupported protocol')
    }
    return url.toString().replace(/\/$/, '')
  } catch {
    throw new Error(`${name} must be a valid HTTP(S) URL`)
  }
}

export const env = Object.freeze({
  apiBaseUrl: httpUrl('VITE_API_BASE_URL', import.meta.env.VITE_API_BASE_URL),
  supabaseUrl: httpUrl('VITE_SUPABASE_URL', import.meta.env.VITE_SUPABASE_URL),
  supabaseAnonKey: required(
    'VITE_SUPABASE_ANON_KEY',
    import.meta.env.VITE_SUPABASE_ANON_KEY,
  ),
})
