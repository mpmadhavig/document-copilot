import { reportFrontendError } from './clientLogger'

const DEFAULT_TIMEOUT_MS = 15_000

type AccessTokenProvider = () => Promise<string | null>
type UnauthorizedHandler = () => Promise<void>

export type RequestOptions = Omit<RequestInit, 'body' | 'method'> & {
  body?: unknown
  timeoutMs?: number
}

export class ApiError extends Error {
  readonly status: number | null
  readonly body: unknown
  readonly isNetworkError: boolean
  readonly reference: string
  readonly backendReference: string | null

  constructor(
    message: string,
    options: {
      status?: number
      body?: unknown
      isNetworkError?: boolean
      cause?: unknown
      reference: string
      backendReference?: string
    },
  ) {
    super(message, { cause: options.cause })
    this.name = 'ApiError'
    this.status = options.status ?? null
    this.body = options.body
    this.isNetworkError = options.isNetworkError ?? false
    this.reference = options.reference
    this.backendReference = options.backendReference ?? null
  }
}

async function responseBody(response: Response): Promise<unknown> {
  if (response.status === 204) return undefined

  const contentType = response.headers.get('content-type')
  return contentType?.includes('application/json')
    ? response.json()
    : response.text()
}

export class HttpClient {
  private readonly baseUrl: string
  private readonly getAccessToken: AccessTokenProvider
  private readonly onUnauthorized: UnauthorizedHandler | undefined

  constructor(
    baseUrl: string,
    getAccessToken: AccessTokenProvider,
    onUnauthorized?: UnauthorizedHandler,
  ) {
    this.baseUrl = baseUrl
    this.getAccessToken = getAccessToken
    this.onUnauthorized = onUnauthorized
  }

  get<T>(path: string, options?: RequestOptions): Promise<T> {
    return this.request<T>('GET', path, options)
  }

  post<T>(path: string, body?: unknown, options?: RequestOptions): Promise<T> {
    return this.request<T>('POST', path, { ...options, body })
  }

  put<T>(path: string, body?: unknown, options?: RequestOptions): Promise<T> {
    return this.request<T>('PUT', path, { ...options, body })
  }

  patch<T>(path: string, body?: unknown, options?: RequestOptions): Promise<T> {
    return this.request<T>('PATCH', path, { ...options, body })
  }

  delete<T>(path: string, options?: RequestOptions): Promise<T> {
    return this.request<T>('DELETE', path, options)
  }

  async request<T>(
    method: string,
    path: string,
    options: RequestOptions = {},
  ): Promise<T> {
    const { body, headers: suppliedHeaders, timeoutMs, ...requestInit } = options
    const headers = new Headers(suppliedHeaders)
    const accessToken = await this.getAccessToken()

    if (accessToken) headers.set('Authorization', `Bearer ${accessToken}`)
    if (body !== undefined && !headers.has('Content-Type')) {
      headers.set('Content-Type', 'application/json')
    }

    const signal = AbortSignal.any([
      AbortSignal.timeout(timeoutMs ?? DEFAULT_TIMEOUT_MS),
      ...(requestInit.signal ? [requestInit.signal] : []),
    ])

    let response: Response
    try {
      response = await fetch(`${this.baseUrl}/${path.replace(/^\//, '')}`, {
        ...requestInit,
        method,
        headers,
        body: body === undefined ? undefined : JSON.stringify(body),
        signal,
      })
    } catch (error) {
      const reference = reportFrontendError(error, {
        area: 'api',
        action: `${method} ${path}`,
      })
      throw new ApiError('Unable to reach the API', {
        isNetworkError: true,
        cause: error,
        reference: reference.id,
      })
    }

    const parsedBody = await responseBody(response)
    if (!response.ok) {
      if (response.status === 401) await this.onUnauthorized?.()
      const backendReference = readBackendReference(parsedBody)
      const reference = reportFrontendError(
        new Error(`API request failed with status ${response.status}`),
        {
          area: 'api',
          action: `${method} ${path}`,
          backendReference: backendReference ?? undefined,
        },
      )
      throw new ApiError(`API request failed with status ${response.status}`, {
        status: response.status,
        body: parsedBody,
        reference: reference.id,
        backendReference: backendReference ?? undefined,
      })
    }
    return parsedBody as T
  }
}

function readBackendReference(body: unknown): string | null {
  if (typeof body !== 'object' || body === null) return null
  const reference = (body as Record<string, unknown>).error_reference
  return typeof reference === 'string' && reference.startsWith('be-')
    ? reference
    : null
}
