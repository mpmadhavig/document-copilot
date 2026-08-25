import type { ReactNode } from 'react'

import {
  messageAnswerStatus,
  messageCitations,
  type CitationData,
  type DocumentChatMessage,
} from '@/lib/chat'
import { CitationChip } from './CitationChip'

type AssistantMessageProps = {
  message: DocumentChatMessage
  selectedPosition: number | null
  onSelectCitation: (citation: CitationData) => void
}

export function AssistantMessage({
  message,
  selectedPosition,
  onSelectCitation,
}: AssistantMessageProps) {
  const citations = messageCitations(message)
  const citationByPosition = new Map(
    citations.map((citation) => [citation.position, citation]),
  )
  const answerStatus = messageAnswerStatus(message)
  const textParts = message.parts.filter((part) => part.type === 'text')
  const isInsufficient = answerStatus === 'insufficient_evidence'
  const isRefused = answerStatus === 'refused'

  return (
    <article className="flex items-start gap-2.5">
      <span className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-cyan-400 via-violet-500 to-indigo-700 text-[9px] font-black text-white shadow-md shadow-violet-200">DC</span>
      <div
        className={`min-w-0 flex-1 rounded-2xl rounded-tl-md border px-4 py-3.5 text-sm leading-6 shadow-sm sm:max-w-[90%] sm:flex-none ${
          isInsufficient
            ? 'border-amber-200 bg-amber-50/90 text-amber-950'
            : isRefused
              ? 'border-slate-300 bg-slate-100/90 text-slate-800'
              : 'border-slate-200/90 bg-white/95 text-slate-800'
        }`}
      >
        <div className="mb-2.5 flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-400">
          <span>Document Copilot</span>
          {answerStatus === 'answered' && (
            <span className="rounded-full bg-emerald-50 px-2 py-0.5 normal-case tracking-normal text-emerald-700">✓ Sources checked</span>
          )}
        </div>
        {isInsufficient && (
          <p className="mb-2 font-semibold">Not enough evidence in the corpus</p>
        )}
        {isRefused && (
          <p className="mb-2 font-semibold">Outside the research scope</p>
        )}
        <div className="whitespace-pre-wrap">
          {textParts.map((part, index) => (
            <span key={index}>
              {renderCitedText(part.text, citationByPosition, onSelectCitation)}
            </span>
          ))}
        </div>
        {citations.length > 0 && (
          <div className="mt-4 border-t border-slate-200/80 pt-3">
            <p className="mb-2 text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-400">Sources used</p>
            <div className="flex flex-wrap gap-2">
            {citations.map((citation) => (
              <CitationChip
                key={`${citation.position}-${citation.chunkId}`}
                citation={citation}
                isSelected={selectedPosition === citation.position}
                onSelect={() => onSelectCitation(citation)}
              />
            ))}
            </div>
          </div>
        )}
      </div>
    </article>
  )
}

function renderCitedText(
  text: string,
  citationByPosition: Map<number, CitationData>,
  onSelectCitation: (citation: CitationData) => void,
): ReactNode[] {
  const rendered: ReactNode[] = []
  const marker = /\[(\d+)]/g
  let cursor = 0
  let match: RegExpExecArray | null

  while ((match = marker.exec(text)) !== null) {
    if (match.index > cursor) rendered.push(text.slice(cursor, match.index))
    const citation = citationByPosition.get(Number(match[1]))
    rendered.push(
      citation ? (
        <button
          className="mx-0.5 inline-flex rounded-md border border-violet-200 bg-violet-50 px-1.5 py-0.5 align-baseline text-xs font-bold text-violet-700 transition hover:border-violet-400 hover:bg-violet-100 focus:outline-none focus:ring-2 focus:ring-violet-300"
          key={`citation-${match.index}`}
          type="button"
          aria-label={`Open citation ${citation.position}`}
          onClick={() => onSelectCitation(citation)}
        >
          [{citation.position}]
        </button>
      ) : (
        match[0]
      ),
    )
    cursor = marker.lastIndex
  }

  if (cursor < text.length) rendered.push(text.slice(cursor))
  return rendered
}
