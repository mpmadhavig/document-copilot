import { useState, type FormEvent } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'

import { supabase } from '../../lib/supabase'

export function SignInPage() {
  const location = useLocation()
  const navigate = useNavigate()
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setErrorMessage(null)
    setIsSubmitting(true)

    const form = new FormData(event.currentTarget)
    const email = String(form.get('email')).trim()
    const password = String(form.get('password'))
    const { error } = await supabase.auth.signInWithPassword({ email, password })

    setIsSubmitting(false)
    if (error) {
      setErrorMessage(error.message)
      return
    }
    const requestedPath = location.state as { from?: { pathname?: string } } | null
    navigate(requestedPath?.from?.pathname ?? '/', { replace: true })
  }

  return (
    <main className="flex min-h-svh items-center justify-center bg-slate-50 px-6 py-12">
      <section className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <p className="mb-2 text-sm font-semibold text-violet-700">
          Document Copilot
        </p>
        <h1 className="text-3xl font-semibold tracking-tight text-slate-950">
          Sign in
        </h1>
        <p className="mt-3 text-base text-slate-600">
          Use your email and password to continue.
        </p>

        <form className="mt-8 space-y-5" onSubmit={handleSubmit}>
          <label className="block text-sm font-medium text-slate-800">
            Email address
            <input
              className="mt-2 w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-slate-950 outline-none transition focus:border-violet-600 focus:ring-2 focus:ring-violet-200"
              name="email"
              type="email"
              autoComplete="email"
              required
            />
          </label>

          <label className="block text-sm font-medium text-slate-800">
            Password
            <input
              className="mt-2 w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-slate-950 outline-none transition focus:border-violet-600 focus:ring-2 focus:ring-violet-200"
              name="password"
              type="password"
              autoComplete="current-password"
              required
            />
          </label>

          {errorMessage && (
            <p
              className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700"
              role="alert"
            >
              {errorMessage}
            </p>
          )}

          <button
            className="w-full rounded-lg bg-violet-700 px-4 py-2.5 font-semibold text-white transition hover:bg-violet-800 disabled:cursor-not-allowed disabled:opacity-60"
            type="submit"
            disabled={isSubmitting}
          >
            {isSubmitting ? 'Signing in…' : 'Sign in'}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-slate-600">
          New to Document Copilot?{' '}
          <Link className="font-semibold text-violet-700 hover:text-violet-800" to="/signup">
            Create an account
          </Link>
        </p>
      </section>
    </main>
  )
}
