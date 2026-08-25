import { useState, type FormEvent } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'

import { supabase } from '@/lib/supabase'
import {
  reportFrontendError,
  troubleshootingText,
} from '@/lib/clientLogger'

type AuthMode = 'signin' | 'signup'

type AuthPageProps = {
  initialMode: AuthMode
}

export function AuthPage({ initialMode }: AuthPageProps) {
  const location = useLocation()
  const navigate = useNavigate()
  const mode = initialMode
  const [showPassword, setShowPassword] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [confirmationEmail, setConfirmationEmail] = useState<string | null>(null)

  function selectMode(nextMode: AuthMode) {
    setErrorMessage(null)
    setConfirmationEmail(null)
    navigate(nextMode === 'signin' ? '/signin' : '/signup', {
      replace: true,
      state: location.state,
    })
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setErrorMessage(null)
    setIsSubmitting(true)

    const form = new FormData(event.currentTarget)
    const email = String(form.get('email')).trim()
    const password = String(form.get('password'))

    if (mode === 'signin') {
      const { error } = await supabase.auth.signInWithPassword({ email, password })
      setIsSubmitting(false)
      if (error) {
        const reference = reportFrontendError(error, {
          area: 'auth',
          action: 'sign in',
        })
        setErrorMessage(`${error.message} ${troubleshootingText(reference)}.`)
        return
      }
      const requestedPath = location.state as {
        from?: { pathname?: string }
      } | null
      navigate(requestedPath?.from?.pathname ?? '/chats', { replace: true })
      return
    }

    const { data, error } = await supabase.auth.signUp({
      email,
      password,
      options: { emailRedirectTo: window.location.origin },
    })
    setIsSubmitting(false)
    if (error) {
      const reference = reportFrontendError(error, {
        area: 'auth',
        action: 'sign up',
      })
      setErrorMessage(`${error.message} ${troubleshootingText(reference)}.`)
      return
    }
    if (data.session) {
      navigate('/chats', { replace: true })
      return
    }
    setConfirmationEmail(email)
  }

  return (
    <main className="relative min-h-svh overflow-hidden bg-[#07111f] text-white">
      <div className="pointer-events-none absolute inset-0 auth-aurora" />
      <div className="relative mx-auto grid min-h-svh max-w-7xl items-center gap-12 px-6 py-10 lg:grid-cols-[1.05fr_0.95fr] lg:px-10">
        <section className="hidden max-w-xl lg:block">
          <div className="inline-flex items-center gap-3 rounded-full border border-white/10 bg-white/5 px-3 py-2 text-sm text-cyan-100 backdrop-blur">
            <span className="h-2 w-2 rounded-full bg-cyan-300 shadow-[0_0_18px_#67e8f9]" />
            Private filing intelligence for research teams
          </div>
          <h1 className="mt-8 text-5xl font-semibold leading-[1.08] tracking-[-0.04em]">
            Answers you can trace
            <span className="block bg-gradient-to-r from-cyan-300 to-violet-300 bg-clip-text text-transparent">
              back to the filing.
            </span>
          </h1>
          <p className="mt-6 max-w-lg text-lg leading-8 text-slate-300">
            Research across a curated SEC corpus, compare disclosures over time, and inspect every cited passage before it enters your analysis.
          </p>

          <div className="mt-10 grid max-w-xl grid-cols-3 gap-3">
            <TrustMetric value="25" label="Sample filings" />
            <TrustMetric value="5" label="Companies" />
            <TrustMetric value="100%" label="Cited claims" />
          </div>

          <div className="mt-8 flex items-start gap-3 rounded-2xl border border-white/10 bg-white/[0.04] p-4 text-sm leading-6 text-slate-300 backdrop-blur">
            <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-emerald-400/15 text-emerald-300">✓</span>
            <p>
              Grounding is enforced by the backend. Unsupported answers are withheld rather than presented as research.
            </p>
          </div>
        </section>

        <section className="mx-auto w-full max-w-md">
          <div className="mb-8 flex items-center gap-3 lg:hidden">
            <BrandMark />
            <div>
              <p className="font-semibold">Document Copilot</p>
              <p className="text-xs text-slate-400">Grounded filing research</p>
            </div>
          </div>

          <div className="rounded-[2rem] border border-white/10 bg-white/[0.97] p-2 text-slate-950 shadow-2xl shadow-black/30 backdrop-blur-xl">
            <div className="rounded-[1.55rem] border border-slate-200/80 bg-white p-6 sm:p-8">
              <div className="hidden items-center gap-3 lg:flex">
                <BrandMark />
                <div>
                  <p className="font-semibold text-slate-950">Document Copilot</p>
                  <p className="text-xs text-slate-500">Driftwood research workspace</p>
                </div>
              </div>

              <div className="mt-7 grid grid-cols-2 rounded-xl bg-slate-100 p-1" aria-label="Authentication mode">
                <AuthTab active={mode === 'signin'} onClick={() => selectMode('signin')}>
                  Sign in
                </AuthTab>
                <AuthTab active={mode === 'signup'} onClick={() => selectMode('signup')}>
                  Create account
                </AuthTab>
              </div>

              {confirmationEmail ? (
                <div className="py-10 text-center">
                  <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-emerald-100 text-2xl text-emerald-700">✓</div>
                  <h2 className="mt-5 text-2xl font-semibold tracking-tight">Check your email</h2>
                  <p className="mt-3 text-sm leading-6 text-slate-600">
                    We sent a confirmation link to <strong className="font-semibold text-slate-900">{confirmationEmail}</strong>.
                  </p>
                  <button
                    className="mt-6 text-sm font-semibold text-violet-700 hover:text-violet-900"
                    type="button"
                    onClick={() => selectMode('signin')}
                  >
                    Return to sign in
                  </button>
                </div>
              ) : (
                <>
                  <div className="mt-7">
                    <p className="text-xs font-semibold uppercase tracking-[0.18em] text-violet-700">
                      Analyst access
                    </p>
                    <h2 className="mt-2 text-2xl font-semibold tracking-tight">
                      {mode === 'signin' ? 'Welcome back' : 'Create your workspace access'}
                    </h2>
                    <p className="mt-2 text-sm leading-6 text-slate-500">
                      {mode === 'signin'
                        ? 'Continue to your conversations and filing evidence.'
                        : 'Use your work email to join the research workspace.'}
                    </p>
                  </div>

                  <form className="mt-7 space-y-5" onSubmit={handleSubmit}>
                    <label className="block text-sm font-medium text-slate-700">
                      Work email
                      <input
                        className="mt-2 w-full rounded-xl border border-slate-300 bg-slate-50 px-3.5 py-3 text-slate-950 outline-none transition placeholder:text-slate-400 focus:border-violet-500 focus:bg-white focus:ring-4 focus:ring-violet-100"
                        name="email"
                        type="email"
                        autoComplete="email"
                        placeholder="analyst@driftwood.com"
                        required
                      />
                    </label>

                    <label className="block text-sm font-medium text-slate-700">
                      Password
                      <span className="relative mt-2 block">
                        <input
                          className="w-full rounded-xl border border-slate-300 bg-slate-50 px-3.5 py-3 pr-16 text-slate-950 outline-none transition focus:border-violet-500 focus:bg-white focus:ring-4 focus:ring-violet-100"
                          name="password"
                          type={showPassword ? 'text' : 'password'}
                          autoComplete={mode === 'signin' ? 'current-password' : 'new-password'}
                          minLength={mode === 'signup' ? 8 : undefined}
                          required
                        />
                        <button
                          className="absolute inset-y-0 right-3 text-xs font-semibold text-slate-500 hover:text-slate-900"
                          type="button"
                          onClick={() => setShowPassword((visible) => !visible)}
                        >
                          {showPassword ? 'Hide' : 'Show'}
                        </button>
                      </span>
                      {mode === 'signup' && (
                        <span className="mt-2 block text-xs font-normal text-slate-500">Use at least 8 characters.</span>
                      )}
                    </label>

                    {errorMessage && (
                      <p className="rounded-xl border border-red-200 bg-red-50 px-3.5 py-3 text-sm text-red-700" role="alert">
                        {errorMessage}
                      </p>
                    )}

                    <button
                      className="w-full rounded-xl bg-gradient-to-r from-violet-700 to-indigo-700 px-4 py-3 font-semibold text-white shadow-lg shadow-violet-900/15 transition hover:-translate-y-0.5 hover:shadow-xl disabled:cursor-not-allowed disabled:opacity-60"
                      type="submit"
                      disabled={isSubmitting}
                    >
                      {isSubmitting
                        ? mode === 'signin' ? 'Signing in…' : 'Creating account…'
                        : mode === 'signin' ? 'Open research workspace' : 'Create account'}
                    </button>
                  </form>
                </>
              )}
            </div>
          </div>
          <p className="mt-5 text-center text-xs leading-5 text-slate-400">
            Internal research tool · SEC filing corpus · No investment advice
          </p>
        </section>
      </div>
    </main>
  )
}

function AuthTab({
  active,
  children,
  onClick,
}: {
  active: boolean
  children: string
  onClick: () => void
}) {
  return (
    <button
      className={`rounded-lg px-3 py-2 text-sm font-semibold transition ${
        active ? 'bg-white text-slate-950 shadow-sm' : 'text-slate-500 hover:text-slate-800'
      }`}
      type="button"
      aria-pressed={active}
      onClick={onClick}
    >
      {children}
    </button>
  )
}

function BrandMark() {
  return (
    <span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br from-cyan-400 via-violet-500 to-indigo-700 text-sm font-black tracking-tight text-white shadow-lg shadow-violet-900/20">
      DC
    </span>
  )
}

function TrustMetric({ value, label }: { value: string; label: string }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4 backdrop-blur">
      <p className="text-2xl font-semibold text-white">{value}</p>
      <p className="mt-1 text-xs text-slate-400">{label}</p>
    </div>
  )
}
