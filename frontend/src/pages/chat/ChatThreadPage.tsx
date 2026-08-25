import { useEffect, useState } from 'react'
import { Link, useOutletContext, useParams } from 'react-router-dom'

import { ChatConversation } from '@/components/chat/ChatConversation'
import type { ChatLayoutContext } from '@/components/chat/ChatLayout'
import { api, ApiError } from '@/lib/api'
import {
  ensureErrorReference,
  troubleshootingText,
} from '@/lib/clientLogger'
import {
  asDocumentChatMessage,
  type DocumentChatMessage,
} from '@/lib/chat'

export function ChatThreadPage() {
  const { threadId } = useParams()
  const { threads, refreshThreads } = useOutletContext<ChatLayoutContext>()
  const [loadAttempt, setLoadAttempt] = useState(0)
  const [loaded, setLoaded] = useState<{
    threadId: string
    messages: DocumentChatMessage[] | null
    errorMessage: string | null
    canRetry: boolean
  } | null>(null)
  const thread = threads.find((item) => item.id === threadId)

  useEffect(() => {
    if (!threadId) return

    let isCurrent = true
    void api
      .getMessages(threadId)
      .then((stored) => {
        if (!isCurrent) return
        setLoaded({
          threadId,
          messages: stored.map(asDocumentChatMessage),
          errorMessage: null,
          canRetry: false,
        })
      })
      .catch((error: unknown) => {
        if (!isCurrent) return
        let errorMessage: string
        if (error instanceof ApiError && error.status === 403) {
          errorMessage = 'You do not have access to this conversation.'
        } else if (error instanceof ApiError && error.status === 404) {
          errorMessage = 'This conversation no longer exists.'
        } else {
          errorMessage = 'Unable to load this conversation.'
        }
        const reference = ensureErrorReference(error, {
          area: 'conversation',
          action: 'load messages',
        })
        errorMessage = `${errorMessage} ${troubleshootingText(reference)}.`
        setLoaded({
          threadId,
          messages: null,
          errorMessage,
          canRetry: !(error instanceof ApiError && [403, 404].includes(error.status ?? 0)),
        })
      })

    return () => {
      isCurrent = false
    }
  }, [loadAttempt, threadId])

  if (!threadId) return null
  const isCurrentThreadLoaded = loaded?.threadId === threadId
  const messages = isCurrentThreadLoaded ? loaded.messages : null
  const errorMessage = isCurrentThreadLoaded ? loaded.errorMessage : null
  const canRetry = isCurrentThreadLoaded ? loaded.canRetry : false

  if (errorMessage) {
    return (
      <div className="flex h-full items-center justify-center px-6">
        <div className="text-center">
          <p className="text-slate-700" role="alert">{errorMessage}</p>
          <div className="mt-4 flex justify-center gap-4">
            {canRetry && (
              <button
                className="font-semibold text-violet-700"
                type="button"
                onClick={() => {
                  setLoaded(null)
                  setLoadAttempt((attempt) => attempt + 1)
                }}
              >
                Try again
              </button>
            )}
            <Link className="font-semibold text-violet-700" to="/chats">
              Back to conversations
            </Link>
          </div>
        </div>
      </div>
    )
  }

  if (!messages) {
    return (
      <div className="flex h-full items-center justify-center">
        <p className="text-sm text-slate-500" role="status">Loading messages…</p>
      </div>
    )
  }

  return (
    <ChatConversation
      key={threadId}
      threadId={threadId}
      title={thread?.title ?? 'Conversation'}
      initialMessages={messages}
      onPersisted={refreshThreads}
    />
  )
}
