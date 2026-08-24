import { useState, type FormEvent } from 'react'
import { NavLink } from 'react-router-dom'

import type { ChatThread } from '@/lib/api'

type ThreadSidebarProps = {
  threads: ChatThread[]
  isLoading: boolean
  isCreating: boolean
  errorMessage: string | null
  onCreate: () => void
  onRename: (threadId: string, title: string) => Promise<void>
}

export function ThreadSidebar({
  threads,
  isLoading,
  isCreating,
  errorMessage,
  onCreate,
  onRename,
}: ThreadSidebarProps) {
  const [editingId, setEditingId] = useState<string | null>(null)
  const [renameError, setRenameError] = useState<string | null>(null)

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
    } catch {
      setRenameError('Could not rename this conversation.')
    }
  }

  return (
    <aside className="flex w-72 shrink-0 flex-col border-r border-slate-200 bg-white max-md:w-56">
      <div className="border-b border-slate-200 p-4">
        <p className="text-sm font-semibold text-violet-700">Document Copilot</p>
        <button
          className="mt-4 w-full rounded-lg bg-violet-700 px-3 py-2 text-sm font-semibold text-white transition hover:bg-violet-800 disabled:cursor-not-allowed disabled:opacity-60"
          type="button"
          onClick={onCreate}
          disabled={isCreating}
        >
          {isCreating ? 'Creating…' : '+ New conversation'}
        </button>
      </div>

      <nav className="min-h-0 flex-1 overflow-y-auto p-3" aria-label="Conversations">
        {isLoading && (
          <p className="px-2 py-3 text-sm text-slate-500" role="status">
            Loading conversations…
          </p>
        )}
        {!isLoading && threads.length === 0 && (
          <p className="px-2 py-3 text-sm leading-6 text-slate-500">
            No conversations yet.
          </p>
        )}
        <ul className="space-y-1">
          {threads.map((thread) => (
            <li key={thread.id}>
              {editingId === thread.id ? (
                <form
                  className="rounded-lg bg-slate-100 p-2"
                  onSubmit={(event) => void submitRename(event, thread.id)}
                >
                  <input
                    className="w-full rounded border border-slate-300 bg-white px-2 py-1 text-sm outline-none focus:border-violet-600"
                    name="title"
                    defaultValue={thread.title}
                    maxLength={300}
                    autoFocus
                  />
                  <div className="mt-2 flex gap-2 text-xs">
                    <button className="font-semibold text-violet-700" type="submit">
                      Save
                    </button>
                    <button
                      className="text-slate-500"
                      type="button"
                      onClick={() => setEditingId(null)}
                    >
                      Cancel
                    </button>
                  </div>
                </form>
              ) : (
                <div className="group flex items-center gap-1">
                  <NavLink
                    className={({ isActive }) =>
                      `min-w-0 flex-1 truncate rounded-lg px-3 py-2 text-sm transition ${
                        isActive
                          ? 'bg-violet-50 font-semibold text-violet-800'
                          : 'text-slate-700 hover:bg-slate-100'
                      }`
                    }
                    to={`/chats/${thread.id}`}
                    title={thread.title}
                  >
                    {thread.title}
                  </NavLink>
                  <button
                    className="rounded px-1.5 py-1 text-xs text-slate-400 opacity-0 transition hover:bg-slate-100 hover:text-slate-700 group-hover:opacity-100 focus:opacity-100"
                    type="button"
                    aria-label={`Rename ${thread.title}`}
                    onClick={() => setEditingId(thread.id)}
                  >
                    Edit
                  </button>
                </div>
              )}
            </li>
          ))}
        </ul>
        {(errorMessage || renameError) && (
          <p className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-xs text-red-700" role="alert">
            {renameError ?? errorMessage}
          </p>
        )}
      </nav>
    </aside>
  )
}
