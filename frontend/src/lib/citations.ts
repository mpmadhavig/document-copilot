import type { CitationData } from './chat'

const filingDateFormatter = new Intl.DateTimeFormat(undefined, {
  year: 'numeric',
  month: 'short',
  day: 'numeric',
  timeZone: 'UTC',
})

export function filingDateLabel(value: string): string {
  const date = new Date(`${value}T00:00:00Z`)
  return Number.isNaN(date.getTime()) ? value : filingDateFormatter.format(date)
}

export function filingLabel(citation: CitationData): string {
  const fiscalYear = citation.fiscalYear ? `FY${citation.fiscalYear}` : null
  return [citation.filingType, fiscalYear, filingDateLabel(citation.filingDate)]
    .filter(Boolean)
    .join(' · ')
}

export function sourceLocationLabel(citation: CitationData): string {
  const pages = pageLabel(citation.pages)
  return [pages, citation.section].filter(Boolean).join(' · ') || 'Location unavailable'
}

function pageLabel(pages: number[]): string | null {
  if (pages.length === 0) return null
  if (pages.length === 1) return `p. ${pages[0]}`
  return `pp. ${pages.join(', ')}`
}
