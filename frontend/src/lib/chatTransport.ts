import { clearLocalSession } from './supabase'
import { reportFrontendError } from './clientLogger'

export type ChatTransportErrorKind =
  | 'auth'
  | 'forbidden'
  | 'not-found'
  | 'network'
  | 'request'

export class ChatTransportError extends Error {
  readonly kind: ChatTransportErrorKind
  readonly reference: string
  readonly backendReference: string | null

  constructor(
    kind: ChatTransportErrorKind,
    message: string,
    options: {
      cause?: unknown
      reference: string
      backendReference?: string
    },
  ) {
    super(message, { cause: options.cause })
    this.name = 'ChatTransportError'
    this.kind = kind
    this.reference = options.reference
    this.backendReference = options.backendReference ?? null
  }
}

export async function chatFetch(
  input: RequestInfo | URL,
  init?: RequestInit,
): Promise<Response> {
  let response: Response
  try {
    response = await fetch(input, init)
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error
    throw loggedTransportError(
      'network',
      'Unable to reach the API. Check the connection and CORS configuration.',
      error,
    )
  }

  if (response.ok) return response

  if (response.status === 401) {
    await clearLocalSession()
    throw loggedTransportError(
      'auth',
      'Your session expired. Sign in again to continue.',
    )
  }
  if (response.status === 403) {
    throw loggedTransportError(
      'forbidden',
      'You do not have access to this conversation.',
    )
  }
  if (response.status === 404) {
    throw loggedTransportError(
      'not-found',
      'This conversation no longer exists.',
    )
  }
  const backendReference = await responseBackendReference(response)
  throw loggedTransportError(
    'request',
    'The request could not be completed. Please try again.',
    undefined,
    backendReference,
  )
}

function loggedTransportError(
  kind: ChatTransportErrorKind,
  message: string,
  cause?: unknown,
  backendReference?: string,
): ChatTransportError {
  const reference = reportFrontendError(cause ?? new Error(message), {
    area: 'chat',
    action: `transport ${kind}`,
    backendReference,
  })
  return new ChatTransportError(kind, message, {
    cause,
    reference: reference.id,
    backendReference,
  })
}

async function responseBackendReference(response: Response): Promise<string | undefined> {
  try {
    const body: unknown = await response.clone().json()
    if (typeof body !== 'object' || body === null) return undefined
    const reference = (body as Record<string, unknown>).error_reference
    return typeof reference === 'string' && reference.startsWith('be-')
      ? reference
      : undefined
  } catch {
    return undefined
  }
}
