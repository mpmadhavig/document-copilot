import type { CitationData } from '@/lib/chat'
import { filingLabel, sourceLocationLabel } from '@/lib/citations'

type CitationChipProps = {
  citation: CitationData
  isSelected: boolean
  onSelect: () => void
}

export function CitationChip({
  citation,
  isSelected,
  onSelect,
}: CitationChipProps) {
  return (
    <button
      className={`group min-w-52 rounded-xl border px-3 py-2.5 text-left text-xs transition focus:outline-none focus:ring-4 focus:ring-violet-100 ${
        isSelected
          ? 'border-violet-500 bg-violet-50 text-violet-950 shadow-sm'
          : 'border-slate-200 bg-slate-50/80 text-slate-700 hover:-translate-y-0.5 hover:border-violet-300 hover:bg-violet-50/60 hover:shadow-sm'
      }`}
      type="button"
      aria-label={`Citation ${citation.position}: ${citation.companyName}, ${filingLabel(citation)}, ${sourceLocationLabel(citation)}`}
      aria-pressed={isSelected}
      onClick={onSelect}
    >
      <span className="flex items-start gap-2">
        <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-md bg-violet-100 text-[10px] font-bold text-violet-700">{citation.position}</span>
        <span className="min-w-0">
          <span className="block truncate font-semibold text-slate-950">{citation.companyName} ({citation.ticker})</span>
          <span className="mt-0.5 block">{filingLabel(citation)}</span>
          <span className="mt-0.5 block text-slate-500">{sourceLocationLabel(citation)} · View passage ↗</span>
        </span>
      </span>
    </button>
  )
}
