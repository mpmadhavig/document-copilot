import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { supabase } from '../../lib/supabase'

export function SignUpPage() {
  const navigate = useNavigate()
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [success, setSuccess] = useState<{
    email: string
    requiresConfirmation: boolean
  } | null>(null)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setErrorMessage(null)
    setIsSubmitting(true)

    const form = new FormData(event.currentTarget)
    const email = String(form.get('email')).trim()
    const password = String(form.get('password'))
    const { data, error } = await supabase.auth.signUp({
      email,
      password,
      options: { emailRedirectTo: window.location.origin },
    })

    setIsSubmitting(false)
    if (error) {
      setErrorMessage(error.message)
      return
    }

    if (data.session) {
      navigate('/', { replace: true })
      return
    }
    setSuccess({ email, requiresConfirmation: true })
  }

  if (success) {
    return (
      <main className="flex min-h-svh items-center justify-center bg-slate-50 px-6">
        <section className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
          <p className="mb-2 text-sm font-semibold text-violet-700">
            {success.requiresConfirmation ? 'Almost there' : 'Account created'}
          </p>
          <h1 className="text-3xl font-semibold tracking-tight text-slate-950">
            {success.requiresConfirmation ? 'Check your email' : 'You are signed in'}
          </h1>
          <p className="mt-4 text-base leading-7 text-slate-600">
            {success.requiresConfirmation ? (
              <>
                We sent a confirmation link to{' '}
                <strong className="font-semibold text-slate-900">
                  {success.email}
                </strong>
                . Open it to finish creating your account.
              </>
            ) : (
              'Your account is ready. The authenticated workspace is coming next.'
            )}
          </p>
        </section>
      </main>
    )
  }

  return (
    <main className="flex min-h-svh items-center justify-center bg-slate-50 px-6 py-12">
      <section className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <p className="mb-2 text-sm font-semibold text-violet-700">
          Document Copilot
        </p>
        <h1 className="text-3xl font-semibold tracking-tight text-slate-950">
          Create your account
        </h1>
        <p className="mt-3 text-base text-slate-600">
          Sign up with your work email to start researching filings.
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
              autoComplete="new-password"
              minLength={8}
              required
            />
            <span className="mt-2 block text-xs font-normal text-slate-500">
              Use at least 8 characters.
            </span>
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
            {isSubmitting ? 'Creating account…' : 'Create account'}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-slate-600">
          Already have an account?{' '}
          <Link className="font-semibold text-violet-700 hover:text-violet-800" to="/signin">
            Sign in
          </Link>
        </p>
      </section>
    </main>
  )
}
