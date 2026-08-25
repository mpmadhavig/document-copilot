import { useCallback, useEffect, useState } from 'react'
import { Outlet, useNavigate } from 'react-router-dom'

import { api, ApiError, type ChatThread } from '@/lib/api'
import {
  ensureErrorReference,
  troubleshootingText,
} from '@/lib/clientLogger'
import { clearLocalSession, supabase } from '@/lib/supabase'
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
  const [isSigningOut, setIsSigningOut] = useState(false)
  const [isSidebarOpen, setIsSidebarOpen] = useState(false)
  const [userEmail, setUserEmail] = useState<string | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const refreshThreads = useCallback(async () => {
    const nextThreads = await api.listThreads()
    setThreads(nextThreads)
  }, [])

  const loadThreads = useCallback(async () => {
    setErrorMessage(null)
    setIsLoading(true)
    try {
      await refreshThreads()
    } catch (error: unknown) {
      setErrorMessage(threadLoadError(error))
    } finally {
      setIsLoading(false)
    }
  }, [refreshThreads])

  useEffect(() => {
    void api
      .listThreads()
      .then(setThreads)
      .catch((error: unknown) => setErrorMessage(threadLoadError(error)))
      .finally(() => setIsLoading(false))
  }, [])

  useEffect(() => {
    void supabase.auth.getSession().then(({ data }) => {
      setUserEmail(data.session?.user.email ?? null)
    })
  }, [])

  async function createThread() {
    setErrorMessage(null)
    setIsCreating(true)
    try {
      const thread = await api.createThread('New research thread')
      setThreads((current) => [thread, ...current])
      setIsSidebarOpen(false)
      navigate(`/chats/${thread.id}`)
    } catch (error: unknown) {
      const reference = ensureErrorReference(error, {
        area: 'conversations',
        action: 'create thread',
      })
      setErrorMessage(
        `Unable to create a conversation. ${troubleshootingText(reference)}.`,
      )
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

  async function signOut() {
    setIsSigningOut(true)
    try {
      await clearLocalSession()
      navigate('/signin', { replace: true })
    } catch (error: unknown) {
      const reference = ensureErrorReference(error, {
        area: 'auth',
        action: 'sign out',
      })
      setErrorMessage(`Unable to log out. ${troubleshootingText(reference)}.`)
      setIsSigningOut(false)
    }
  }

  return (
    <main className="flex h-svh overflow-hidden bg-[#f4f6fb] text-slate-950">
      {isSidebarOpen && (
        <button
          className="fixed inset-0 z-30 bg-slate-950/50 backdrop-blur-sm lg:hidden"
          type="button"
          aria-label="Close conversations"
          onClick={() => setIsSidebarOpen(false)}
        />
      )}
      <ThreadSidebar
        threads={threads}
        isOpen={isSidebarOpen}
        isLoading={isLoading}
        isCreating={isCreating}
        isSigningOut={isSigningOut}
        userEmail={userEmail}
        errorMessage={errorMessage}
        onClose={() => setIsSidebarOpen(false)}
        onCreate={() => void createThread()}
        onRename={renameThread}
        onRetry={() => void loadThreads()}
        onSignOut={() => void signOut()}
      />
      <section className="flex h-svh min-w-0 flex-1 flex-col">
        <div className="flex h-14 shrink-0 items-center justify-between border-b border-slate-200/80 bg-white/90 px-4 backdrop-blur lg:hidden">
          <button
            className="flex h-9 w-9 items-center justify-center rounded-xl border border-slate-200 bg-white text-lg text-slate-700 shadow-sm"
            type="button"
            aria-label="Open conversations"
            onClick={() => setIsSidebarOpen(true)}
          >
            ☰
          </button>
          <div className="flex items-center gap-2">
            <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-gradient-to-br from-cyan-400 to-violet-700 text-[10px] font-black text-white">DC</span>
            <p className="text-sm font-semibold">Document Copilot</p>
          </div>
          <span className="h-9 w-9" aria-hidden="true" />
        </div>
        <div className="min-h-0 flex-1">
          <Outlet context={{ threads, refreshThreads } satisfies ChatLayoutContext} />
        </div>
      </section>
    </main>
  )
}

function threadLoadError(error: unknown): string {
  const message = error instanceof ApiError && error.isNetworkError
    ? 'Document Copilot is unreachable. Check the API URL and CORS settings.'
    : 'Unable to load your conversations.'
  const reference = ensureErrorReference(error, {
    area: 'conversations',
    action: 'load threads',
  })
  return `${message} ${troubleshootingText(reference)}.`
}
