import { useEffect, useState } from 'react'
import { Link, useOutletContext, useParams } from 'react-router-dom'
import type { UIMessage } from 'ai'

import { ChatConversation } from '@/components/chat/ChatConversation'
import type { ChatLayoutContext } from '@/components/chat/ChatLayout'
import { api, ApiError } from '@/lib/api'

export function ChatThreadPage() {
  const { threadId } = useParams()
  const { threads, refreshThreads } = useOutletContext<ChatLayoutContext>()
  const [loaded, setLoaded] = useState<{
    threadId: string
    messages: UIMessage[] | null
    errorMessage: string | null
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
          messages: stored.map(
            ({ id, role, parts }) => ({ id, role, parts }) as UIMessage,
          ),
          errorMessage: null,
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
        setLoaded({ threadId, messages: null, errorMessage })
      })

    return () => {
      isCurrent = false
    }
  }, [threadId])

  if (!threadId) return null
  const isCurrentThreadLoaded = loaded?.threadId === threadId
  const messages = isCurrentThreadLoaded ? loaded.messages : null
  const errorMessage = isCurrentThreadLoaded ? loaded.errorMessage : null

  if (errorMessage) {
    return (
      <div className="flex min-h-svh items-center justify-center px-6">
        <div className="text-center">
          <p className="text-slate-700" role="alert">{errorMessage}</p>
          <Link className="mt-4 inline-block font-semibold text-violet-700" to="/chats">
            Back to conversations
          </Link>
        </div>
      </div>
    )
  }

  if (!messages) {
    return (
      <div className="flex min-h-svh items-center justify-center">
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
