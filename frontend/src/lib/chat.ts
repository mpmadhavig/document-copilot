import type { UIMessage } from 'ai'

export type AnswerStatus = 'answered' | 'insufficient_evidence' | 'refused'

export type ChatErrorCode =
  | 'retrieval_failed'
  | 'grounding_failed'
  | 'assistant_failed'
  | 'persistence_failed'

export type CitationData = {
  position: number
  chunkId: string
  quote: string
  ticker: string
  companyName: string
  filingType: string
  fiscalYear: number | null
  filingDate: string
  pages: number[]
  section: string | null
  accessionNumber: string
  sourceUrl: string
}

export type ChatDataParts = {
  citation: CitationData
  'answer-status': { status: AnswerStatus }
  'chat-error': { code: ChatErrorCode; reference: string }
}

export type DocumentChatMessage = UIMessage<unknown, ChatDataParts>

export function asDocumentChatMessage(message: {
  id: string
  role: 'user' | 'assistant' | 'system'
  parts: Array<Record<string, unknown>>
}): DocumentChatMessage {
  return message as DocumentChatMessage
}

export function messageText(message: DocumentChatMessage): string {
  return message.parts
    .filter((part) => part.type === 'text')
    .map((part) => part.text)
    .join('')
}

export function messageCitations(message: DocumentChatMessage): CitationData[] {
  return message.parts
    .filter((part) => part.type === 'data-citation')
    .map((part) => part.data)
    .filter(isCitationData)
    .sort((left, right) => left.position - right.position)
}

export function messageAnswerStatus(
  message: DocumentChatMessage,
): AnswerStatus | null {
  const part = message.parts.find((item) => item.type === 'data-answer-status')
  const data: unknown = part?.data
  return isRecord(data) && isAnswerStatus(data.status) ? data.status : null
}

function isCitationData(value: unknown): value is CitationData {
  if (!isRecord(value)) return false
  return (
    typeof value.position === 'number' &&
    typeof value.chunkId === 'string' &&
    typeof value.quote === 'string' &&
    typeof value.ticker === 'string' &&
    typeof value.companyName === 'string' &&
    typeof value.filingType === 'string' &&
    (typeof value.fiscalYear === 'number' || value.fiscalYear === null) &&
    typeof value.filingDate === 'string' &&
    Array.isArray(value.pages) &&
    value.pages.every((page) => typeof page === 'number') &&
    (typeof value.section === 'string' || value.section === null) &&
    typeof value.accessionNumber === 'string' &&
    typeof value.sourceUrl === 'string'
  )
}

function isAnswerStatus(value: unknown): value is AnswerStatus {
  return (
    value === 'answered' ||
    value === 'insufficient_evidence' ||
    value === 'refused'
  )
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}
