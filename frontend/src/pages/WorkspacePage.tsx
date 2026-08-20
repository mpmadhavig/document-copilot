import { useEffect, useState } from 'react'

import { api, ApiError, type AuthenticatedUser } from '../lib/api'

export function WorkspacePage() {
  const [user, setUser] = useState<AuthenticatedUser | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  useEffect(() => {
    void api
      .getCurrentUser()
      .then(setUser)
      .catch((error: unknown) => {
        setErrorMessage(
          error instanceof ApiError
            ? 'The backend could not verify your session.'
            : 'Unable to verify your session.',
        )
      })
  }, [])

  return (
    <main className="flex min-h-svh items-center justify-center bg-slate-50 px-6">
      <section className="w-full max-w-2xl rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <p className="mb-2 text-sm font-semibold text-violet-700">
          Document Copilot
        </p>
        <h1 className="text-3xl font-semibold tracking-tight text-slate-950">
          Your workspace
        </h1>
        {user ? (
          <p className="mt-4 text-slate-600">
            Backend authentication verified for{' '}
            <strong className="font-semibold text-slate-900">
              {user.email ?? user.id}
            </strong>
            .
          </p>
        ) : (
          <p className="mt-4 text-slate-600" role="status">
            {errorMessage ?? 'Verifying your session with the backend…'}
          </p>
        )}
      </section>
    </main>
  )
}
