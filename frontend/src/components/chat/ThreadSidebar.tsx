import { useMemo, useState, type FormEvent } from 'react'
import { NavLink } from 'react-router-dom'

import type { ChatThread } from '@/lib/api'
import {
  ensureErrorReference,
  troubleshootingText,
} from '@/lib/clientLogger'

const threadDateFormatter = new Intl.DateTimeFormat(undefined, {
  month: 'short',
  day: 'numeric',
})

type ThreadSidebarProps = {
  threads: ChatThread[]
  isOpen: boolean
  isLoading: boolean
  isCreating: boolean
  isSigningOut: boolean
  userEmail: string | null
  errorMessage: string | null
  onClose: () => void
  onCreate: () => void
  onRename: (threadId: string, title: string) => Promise<void>
  onRetry: () => void
  onSignOut: () => void
}

export function ThreadSidebar({
  threads,
  isOpen,
  isLoading,
  isCreating,
  isSigningOut,
  userEmail,
  errorMessage,
  onClose,
  onCreate,
  onRename,
  onRetry,
  onSignOut,
}: ThreadSidebarProps) {
  const [editingId, setEditingId] = useState<string | null>(null)
  const [renameError, setRenameError] = useState<string | null>(null)
  const [query, setQuery] = useState('')
  const visibleThreads = useMemo(() => {
    const normalized = query.trim().toLocaleLowerCase()
    return normalized
      ? threads.filter((thread) => thread.title.toLocaleLowerCase().includes(normalized))
      : threads
  }, [query, threads])

  async function submitRename(
    event: FormEvent<HTMLFormElement>,
    threadId: string,
  ) {
    event.preventDefault()
    const title = String(new FormData(event.currentTarget).get('title')).trim()
    if (!title) return

    setRenameError(null)
    try {
      await onRename(threadId, title)
      setEditingId(null)
    } catch (error: unknown) {
      const reference = ensureErrorReference(error, {
        area: 'conversations',
        action: 'rename thread',
      })
      setRenameError(
        `Could not rename this conversation. ${troubleshootingText(reference)}.`,
      )
    }
  }

  return (
    <aside
      className={`fixed inset-y-0 left-0 z-40 flex w-[19rem] shrink-0 transform flex-col border-r border-white/10 bg-[#081321] text-white shadow-2xl transition-transform duration-300 lg:static lg:translate-x-0 lg:shadow-none ${
        isOpen ? 'translate-x-0' : '-translate-x-full'
      }`}
    >
      <div className="border-b border-white/10 p-5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-2xl bg-gradient-to-br from-cyan-400 via-violet-500 to-indigo-700 text-xs font-black tracking-tight shadow-lg shadow-violet-950/40">DC</span>
            <div>
              <p className="font-semibold tracking-tight">Document Copilot</p>
              <p className="text-[11px] text-slate-400">Filing research workspace</p>
            </div>
          </div>
          <button
            className="rounded-lg px-2 py-1 text-slate-400 hover:bg-white/10 hover:text-white lg:hidden"
            type="button"
            aria-label="Close conversations"
            onClick={onClose}
          >
            ✕
          </button>
        </div>

        <button
          className="mt-5 flex w-full items-center justify-between rounded-xl bg-gradient-to-r from-violet-600 to-indigo-600 px-4 py-3 text-sm font-semibold text-white shadow-lg shadow-violet-950/30 transition hover:-translate-y-0.5 hover:from-violet-500 hover:to-indigo-500 disabled:cursor-not-allowed disabled:opacity-60"
          type="button"
          onClick={onCreate}
          disabled={isCreating}
        >
          <span>{isCreating ? 'Creating research thread…' : 'New research thread'}</span>
          <span className="text-lg leading-none">＋</span>
        </button>
      </div>

      <div className="px-4 pt-4">
        <label className="relative block">
          <span className="sr-only">Search conversations</span>
          <span className="pointer-events-none absolute inset-y-0 left-3 flex items-center text-sm text-slate-500">⌕</span>
          <input
            className="w-full rounded-xl border border-white/10 bg-white/[0.06] py-2.5 pl-9 pr-3 text-sm text-white outline-none placeholder:text-slate-500 focus:border-violet-400/60 focus:bg-white/10"
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search threads"
          />
        </label>
      </div>

      <nav className="min-h-0 flex-1 overflow-y-auto px-3 py-4" aria-label="Conversations">
        <div className="mb-2 flex items-center justify-between px-2">
          <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-500">Recent research</p>
          {!isLoading && <span className="text-[10px] text-slate-600">{threads.length}</span>}
        </div>
        {isLoading && (
          <div className="space-y-2 px-1 py-2" role="status" aria-label="Loading conversations">
            {[0, 1, 2].map((item) => (
              <div className="h-14 animate-pulse rounded-xl bg-white/[0.05]" key={item} />
            ))}
          </div>
        )}
        {!isLoading && !errorMessage && threads.length === 0 && (
          <div className="mx-1 rounded-xl border border-dashed border-white/10 bg-white/[0.03] px-4 py-5 text-sm leading-6 text-slate-400">
            <p className="font-medium text-slate-200">No research threads yet</p>
            <p className="mt-1 text-xs leading-5">Start with a company, disclosure, or year-over-year comparison.</p>
          </div>
        )}
        {!isLoading && query && visibleThreads.length === 0 && threads.length > 0 && (
          <p className="px-3 py-5 text-sm text-slate-400">No threads match “{query}”.</p>
        )}
        <ul className="space-y-1">
          {visibleThreads.map((thread) => (
            <li key={thread.id}>
              {editingId === thread.id ? (
                <form
                  className="rounded-xl border border-violet-400/30 bg-white/10 p-2.5"
                  onSubmit={(event) => void submitRename(event, thread.id)}
                >
                  <input
                    className="w-full rounded-lg border border-white/15 bg-[#111f31] px-2.5 py-2 text-sm text-white outline-none focus:border-violet-400"
                    name="title"
                    defaultValue={thread.title}
                    maxLength={300}
                    autoFocus
                  />
                  <div className="mt-2 flex gap-3 text-xs">
                    <button className="font-semibold text-cyan-300" type="submit">Save</button>
                    <button className="text-slate-400" type="button" onClick={() => setEditingId(null)}>Cancel</button>
                  </div>
                </form>
              ) : (
                <div className="group relative">
                  <NavLink
                    className={({ isActive }) =>
                      `block min-w-0 rounded-xl px-3 py-2.5 pr-10 transition ${
                        isActive
                          ? 'bg-white/10 text-white shadow-sm ring-1 ring-white/10'
                          : 'text-slate-300 hover:bg-white/[0.06] hover:text-white'
                      }`
                    }
                    to={`/chats/${thread.id}`}
                    title={thread.title}
                    onClick={onClose}
                  >
                    <span className="block truncate text-sm font-medium">{thread.title}</span>
                    <span className="mt-1 block text-[10px] text-slate-500">{threadDateLabel(thread.updated_at)}</span>
                  </NavLink>
                  <button
                    className="absolute right-2 top-2.5 rounded-lg px-2 py-1 text-xs text-slate-500 opacity-0 transition hover:bg-white/10 hover:text-white group-hover:opacity-100 focus:opacity-100"
                    type="button"
                    aria-label={`Rename ${thread.title}`}
                    onClick={() => setEditingId(thread.id)}
                  >
                    •••
                  </button>
                </div>
              )}
            </li>
          ))}
        </ul>
        {(errorMessage || renameError) && (
          <div className="mt-3 rounded-xl border border-red-400/20 bg-red-400/10 px-3 py-2.5 text-xs text-red-200" role="alert">
            <p>{renameError ?? errorMessage}</p>
            {errorMessage && (
              <button className="mt-2 font-semibold text-white underline underline-offset-2" type="button" onClick={onRetry}>Try again</button>
            )}
          </div>
        )}
      </nav>

      <div className="border-t border-white/10 p-3">
        <div className="flex items-center gap-3 rounded-xl px-2 py-2">
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-slate-600 to-slate-800 text-xs font-bold text-white ring-1 ring-white/10">
            {accountInitial(userEmail)}
          </span>
          <div className="min-w-0 flex-1">
            <p className="truncate text-xs font-medium text-slate-200">{userEmail ?? 'Signed-in analyst'}</p>
            <p className="text-[10px] text-emerald-400">● Secure session</p>
          </div>
          <button
            className="rounded-lg px-2 py-1.5 text-xs font-medium text-slate-400 transition hover:bg-white/10 hover:text-white disabled:opacity-50"
            type="button"
            onClick={onSignOut}
            disabled={isSigningOut}
          >
            {isSigningOut ? '…' : 'Log out'}
          </button>
        </div>
      </div>
    </aside>
  )
}

function accountInitial(email: string | null): string {
  return email?.trim().charAt(0).toLocaleUpperCase() || 'A'
}

function threadDateLabel(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return 'Saved conversation'
  return `Updated ${threadDateFormatter.format(date)}`
}
