import type { ChatErrorCode } from '@/lib/chat'
import { ChatTransportError } from '@/lib/chatTransport'
import {
  BACKEND_LOG_FILE,
  referencedError,
  troubleshootingText,
  type ErrorReference,
} from '@/lib/clientLogger'

type ChatErrorNoticeProps = {
  error: Error
  streamCode: ChatErrorCode | null
  streamReference: string | null
  canRetry: boolean
  onRetry: () => void
}

export function ChatErrorNotice({
  error,
  streamCode,
  streamReference,
  canRetry,
  onRetry,
}: ChatErrorNoticeProps) {
  const content = errorContent(error, streamCode)
  const reference: ErrorReference | null = streamReference
    ? { id: streamReference, file: BACKEND_LOG_FILE }
    : referencedError(error)

  return (
    <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-900" role="alert">
      <p className="font-semibold">{content.title}</p>
      <p className="mt-1 leading-6 text-red-800">{content.message}</p>
      {reference && (
        <p className="mt-2 break-all font-mono text-[11px] text-red-700">
          {troubleshootingText(reference)}
        </p>
      )}
      {canRetry && (
        <button
          className="mt-3 rounded-lg border border-red-300 bg-white px-3 py-1.5 text-sm font-semibold text-red-800 hover:bg-red-100 focus:outline-none focus:ring-2 focus:ring-red-300"
          type="button"
          onClick={onRetry}
        >
          Try again
        </button>
      )}
    </div>
  )
}

function errorContent(
  error: Error,
  streamCode: ChatErrorCode | null,
): { title: string; message: string } {
  if (streamCode === 'retrieval_failed') {
    return {
      title: 'The filing search failed',
      message: 'The corpus could not be searched. Try the question again in a moment.',
    }
  }
  if (streamCode === 'grounding_failed') {
    return {
      title: 'The answer did not pass source checks',
      message: 'Nothing unsupported was shown. Try again or narrow the question.',
    }
  }
  if (streamCode === 'persistence_failed') {
    return {
      title: 'The answer could not be saved',
      message: 'The response was withheld so the conversation remains consistent.',
    }
  }
  if (streamCode === 'assistant_failed') {
    return {
      title: 'The grounded answer could not be completed',
      message: 'No unverified response was shown. Please try again.',
    }
  }
  if (error instanceof ChatTransportError && error.kind === 'network') {
    return {
      title: 'Document Copilot is unreachable',
      message: 'Check your connection. During local development, also verify the API URL and CORS settings.',
    }
  }
  return {
    title: 'The response could not be completed',
    message: error.message || 'Please try again.',
  }
}
