export const FRONTEND_LOG_FILE = 'frontend/logs/frontend.log'
export const BACKEND_LOG_FILE = 'backend/logs/backend.log'

export type ErrorReference = {
  id: string
  file: typeof FRONTEND_LOG_FILE | typeof BACKEND_LOG_FILE
}

type ErrorContext = {
  area: string
  action: string
  backendReference?: string
}

export function reportFrontendError(
  error: unknown,
  context: ErrorContext,
): ErrorReference {
  const reference = `fe-${crypto.randomUUID().slice(0, 13)}`
  const normalized = normalizeError(error)
  const report = {
    reference,
    area: context.area,
    action: context.action,
    errorName: normalized.name,
    message: normalized.message,
    stack: normalized.stack ?? '',
    route: window.location.pathname,
    userAgent: navigator.userAgent,
    backendReference: context.backendReference ?? '',
  }

  void fetch('/__client-log', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(report),
    keepalive: true,
  }).catch(() => {
    console.error(`[${reference}] Frontend error log delivery failed`, normalized)
  })

  return { id: reference, file: FRONTEND_LOG_FILE }
}

export function installGlobalErrorLogging(): void {
  window.addEventListener('error', (event) => {
    reportFrontendError(event.error ?? event.message, {
      area: 'window',
      action: 'uncaught error',
    })
  })
  window.addEventListener('unhandledrejection', (event) => {
    reportFrontendError(event.reason, {
      area: 'window',
      action: 'unhandled promise rejection',
    })
  })
}

export function troubleshootingText(reference: ErrorReference): string {
  return `Reference ${reference.id} in ${reference.file}`
}

export function referencedError(error: unknown): ErrorReference | null {
  if (typeof error !== 'object' || error === null) return null
  const value = error as Record<string, unknown>
  if (typeof value.backendReference === 'string' && value.backendReference) {
    return { id: value.backendReference, file: BACKEND_LOG_FILE }
  }
  if (typeof value.reference === 'string' && value.reference) {
    return { id: value.reference, file: FRONTEND_LOG_FILE }
  }
  return null
}

export function ensureErrorReference(
  error: unknown,
  context: ErrorContext,
): ErrorReference {
  return referencedError(error) ?? reportFrontendError(error, context)
}

function normalizeError(error: unknown): Error {
  if (error instanceof Error) return error
  if (typeof error === 'string') return new Error(error)
  return new Error('Unknown frontend error')
}
