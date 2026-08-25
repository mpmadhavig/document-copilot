import { useEffect, useRef } from 'react'

import type { CitationData } from '@/lib/chat'
import { filingLabel, sourceLocationLabel } from '@/lib/citations'

type SourcePassagePanelProps = {
  citation: CitationData
  onClose: () => void
}

export function SourcePassagePanel({
  citation,
  onClose,
}: SourcePassagePanelProps) {
  const heading = useRef<HTMLHeadingElement | null>(null)
  const sourceUrl = safeExternalUrl(citation.sourceUrl)

  useEffect(() => {
    const trigger =
      document.activeElement instanceof HTMLElement
        ? document.activeElement
        : null
    return () => trigger?.focus()
  }, [])

  useEffect(() => {
    heading.current?.focus()
  }, [citation])

  useEffect(() => {
    function closeOnEscape(event: KeyboardEvent) {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', closeOnEscape)
    return () => window.removeEventListener('keydown', closeOnEscape)
  }, [onClose])

  return (
    <aside
      className="source-panel absolute inset-0 z-10 flex min-h-0 flex-col border-l border-slate-200 bg-white shadow-2xl lg:static lg:w-[25rem] lg:shrink-0 lg:shadow-none"
      aria-label="Source passage"
    >
      <div className="flex items-start justify-between gap-4 bg-gradient-to-br from-[#0b1728] to-[#17243a] px-5 py-5 text-white">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-cyan-300">
            Verified source · Citation {citation.position}
          </p>
          <h2
            className="mt-1.5 text-lg font-semibold text-white outline-none"
            ref={heading}
            tabIndex={-1}
          >
            {citation.companyName} ({citation.ticker})
          </h2>
        </div>
        <button
          className="rounded-lg border border-white/10 bg-white/5 px-2.5 py-1.5 text-xs text-slate-300 hover:bg-white/10 hover:text-white focus:outline-none focus:ring-2 focus:ring-cyan-300"
          type="button"
          aria-label="Close source passage"
          onClick={onClose}
        >
          Close
        </button>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto bg-[#fbfcfe] p-5">
        <dl className="grid grid-cols-2 gap-2 text-sm">
          <SourceFact label="Filing" value={filingLabel(citation)} />
          <SourceFact label="Location" value={sourceLocationLabel(citation)} />
          <div className="col-span-2 rounded-xl border border-slate-200 bg-white px-3.5 py-3">
            <dt className="text-[10px] font-semibold uppercase tracking-[0.15em] text-slate-400">SEC accession</dt>
            <dd className="mt-1 break-all font-mono text-xs text-slate-700">{citation.accessionNumber}</dd>
          </div>
        </dl>

        <div className="mt-6 rounded-2xl border border-violet-100 bg-white p-4 shadow-sm">
          <div className="flex items-center justify-between gap-3">
            <h3 className="text-sm font-semibold text-slate-950">Supporting passage</h3>
            <span className="rounded-full bg-emerald-50 px-2 py-1 text-[10px] font-semibold text-emerald-700">Exact quote</span>
          </div>
          <blockquote className="mt-3 whitespace-pre-wrap border-l-4 border-violet-400 bg-violet-50/60 px-4 py-3 text-sm leading-6 text-slate-800">
            {citation.quote}
          </blockquote>
          <p className="mt-2 text-xs leading-5 text-slate-500">
            This quote was checked against the retrieved filing passage before the answer was shown.
          </p>
        </div>

        {sourceUrl && (
          <a
            className="mt-5 flex w-full items-center justify-center rounded-xl bg-gradient-to-r from-violet-700 to-indigo-700 px-4 py-3 text-sm font-semibold text-white shadow-md transition hover:-translate-y-0.5 hover:shadow-lg focus:outline-none focus:ring-4 focus:ring-violet-100"
            href={sourceUrl}
            target="_blank"
            rel="noreferrer"
          >
            Open original filing
          </a>
        )}
      </div>
    </aside>
  )
}

function SourceFact({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white px-3.5 py-3">
      <dt className="text-[10px] font-semibold uppercase tracking-[0.15em] text-slate-400">{label}</dt>
      <dd className="mt-1 text-xs font-medium leading-5 text-slate-800">{value}</dd>
    </div>
  )
}

function safeExternalUrl(value: string): string | null {
  try {
    const url = new URL(value)
    return url.protocol === 'https:' || url.protocol === 'http:' ? url.href : null
  } catch {
    return null
  }
}
