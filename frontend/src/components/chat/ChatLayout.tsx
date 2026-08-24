import { useCallback, useEffect, useState } from 'react'
import { Outlet, useNavigate } from 'react-router-dom'

import { api, ApiError, type ChatThread } from '@/lib/api'
import { ThreadSidebar } from './ThreadSidebar'

export type ChatLayoutContext = {
  threads: ChatThread[]
  refreshThreads: () => Promise<void>
}

export function ChatLayout() {
  const navigate = useNavigate()
  const [threads, setThreads] = useState<ChatThread[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isCreating, setIsCreating] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const refreshThreads = useCallback(async () => {
    const nextThreads = await api.listThreads()
    setThreads(nextThreads)
  }, [])

  useEffect(() => {
    void api
      .listThreads()
      .then(setThreads)
      .catch((error: unknown) => {
        setErrorMessage(
          error instanceof ApiError
            ? 'Unable to load your conversations.'
            : 'Something went wrong while loading conversations.',
        )
      })
      .finally(() => setIsLoading(false))
  }, [])

  async function createThread() {
    setErrorMessage(null)
    setIsCreating(true)
    try {
      const thread = await api.createThread('New chat')
      setThreads((current) => [thread, ...current])
      navigate(`/chats/${thread.id}`)
    } catch {
      setErrorMessage('Unable to create a conversation. Please try again.')
    } finally {
      setIsCreating(false)
    }
  }

  async function renameThread(threadId: string, title: string) {
    const updated = await api.renameThread(threadId, title)
    setThreads((current) =>
      current.map((thread) => (thread.id === threadId ? updated : thread)),
    )
  }

  return (
    <main className="flex min-h-svh bg-slate-50 text-slate-950">
      <ThreadSidebar
        threads={threads}
        isLoading={isLoading}
        isCreating={isCreating}
        errorMessage={errorMessage}
        onCreate={() => void createThread()}
        onRename={renameThread}
      />
      <section className="min-w-0 flex-1">
        <Outlet context={{ threads, refreshThreads } satisfies ChatLayoutContext} />
      </section>
    </main>
  )
}
