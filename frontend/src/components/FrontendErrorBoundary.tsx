import { Component, type ErrorInfo, type ReactNode } from 'react'

import {
  reportFrontendError,
  troubleshootingText,
  type ErrorReference,
} from '@/lib/clientLogger'

type FrontendErrorBoundaryProps = { children: ReactNode }
type FrontendErrorBoundaryState = {
  failed: boolean
  reference: ErrorReference | null
}

export class FrontendErrorBoundary extends Component<
  FrontendErrorBoundaryProps,
  FrontendErrorBoundaryState
> {
  state: FrontendErrorBoundaryState = { failed: false, reference: null }

  static getDerivedStateFromError(): Partial<FrontendErrorBoundaryState> {
    return { failed: true }
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    const reference = reportFrontendError(error, {
      area: 'react',
      action: `render failure: ${info.componentStack?.slice(0, 120) ?? 'unknown component'}`,
    })
    this.setState({ reference })
  }

  render(): ReactNode {
    if (!this.state.failed) return this.props.children

    return (
      <main className="flex min-h-svh items-center justify-center bg-slate-950 px-6 text-white">
        <section className="w-full max-w-lg rounded-3xl border border-white/10 bg-white/5 p-8 text-center shadow-2xl">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-violet-300">
            Document Copilot
          </p>
          <h1 className="mt-3 text-2xl font-semibold">The interface stopped unexpectedly</h1>
          <p className="mt-3 text-sm leading-6 text-slate-300">
            Reload the page to continue. The technical details were written to the frontend log.
          </p>
          {this.state.reference && (
            <p className="mt-4 break-all rounded-xl bg-black/20 px-3 py-2 font-mono text-xs text-slate-300">
              {troubleshootingText(this.state.reference)}
            </p>
          )}
          <button
            className="mt-6 rounded-xl bg-violet-600 px-4 py-2.5 text-sm font-semibold hover:bg-violet-500"
            type="button"
            onClick={() => window.location.reload()}
          >
            Reload application
          </button>
        </section>
      </main>
    )
  }
}
