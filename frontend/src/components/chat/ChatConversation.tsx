import { useEffect, useMemo, useRef, useState, type FormEvent } from 'react'
import { useChat } from '@ai-sdk/react'
import { DefaultChatTransport } from 'ai'

import { api } from '@/lib/api'
import {
  asDocumentChatMessage,
  messageAnswerStatus,
  messageCitations,
  messageText,
  type ChatErrorCode,
  type CitationData,
  type DocumentChatMessage,
} from '@/lib/chat'
import { chatFetch } from '@/lib/chatTransport'
import { env } from '@/lib/env'
import { getAccessToken } from '@/lib/supabase'
import { AssistantMessage } from './AssistantMessage'
import { ChatErrorNotice } from './ChatErrorNotice'
import { SourcePassagePanel } from './SourcePassagePanel'

type ChatConversationProps = {
  threadId: string
  title: string
  initialMessages: DocumentChatMessage[]
  onPersisted: () => Promise<void>
}

type SelectedCitation = {
  messageId: string
  citation: CitationData
}

const EXAMPLE_QUESTIONS = [
  {
    label: 'Track a trend',
    text: 'How did Apple describe Services revenue growth in its latest 10-K?',
  },
  {
    label: 'Compare filings',
    text: 'Compare Microsoft cloud capacity constraints across the available filings.',
  },
  {
    label: 'Review risk',
    text: 'How did NVIDIA describe supply constraints from fiscal 2021 through 2025?',
  },
  {
    label: 'Test the evidence',
    text: 'Do the filings prove generative AI improved margins for any company?',
  },
]

export function ChatConversation({
  threadId,
  title,
  initialMessages,
  onPersisted,
}: ChatConversationProps) {
  const [input, setInput] = useState('')
  const [selectedCitation, setSelectedCitation] =
    useState<SelectedCitation | null>(null)
  const [streamErrorCode, setStreamErrorCode] =
    useState<ChatErrorCode | null>(null)
  const [streamErrorReference, setStreamErrorReference] = useState<string | null>(null)
  const [failedPrompt, setFailedPrompt] = useState<string | null>(null)
  const recoveredError = useRef<Error | null>(null)
  const lastSubmittedText = useRef<string | null>(null)
  const messagesEnd = useRef<HTMLDivElement | null>(null)
  const transport = useMemo(
    () =>
      new DefaultChatTransport<DocumentChatMessage>({
        api: `${env.apiBaseUrl}/chat/stream`,
        fetch: chatFetch,
        headers: async (): Promise<Record<string, string>> => {
          const accessToken = await getAccessToken()
          return accessToken ? { Authorization: `Bearer ${accessToken}` } : {}
        },
        prepareSendMessagesRequest: ({ messages }) => ({
          body: { threadId, messages },
        }),
      }),
    [threadId],
  )

  const {
    messages,
    sendMessage,
    status,
    error,
    setMessages,
    clearError,
    stop,
  } = useChat<DocumentChatMessage>({
    id: threadId,
    messages: initialMessages,
    transport,
    onData: (part) => {
      if (part.type !== 'data-chat-error') return
      setStreamErrorCode(part.data.code)
      setStreamErrorReference(part.data.reference)
    },
    onError: () => {
      setFailedPrompt(lastSubmittedText.current)
    },
    onFinish: ({ isError }) => {
      if (!isError) {
        lastSubmittedText.current = null
        setFailedPrompt(null)
        void onPersisted()
      }
    },
  })

  const isStreaming = status === 'submitted' || status === 'streaming'
  const latestMessage = messages.at(-1)
  const isDeliveringText =
    latestMessage?.role === 'assistant' && Boolean(messageText(latestMessage))

  useEffect(() => {
    messagesEnd.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, status])

  useEffect(() => {
    if (!error || recoveredError.current === error) return
    recoveredError.current = error
    void api.getMessages(threadId).then((stored) => {
      const recovered = stored.map(asDocumentChatMessage)
      setMessages(recovered)
      setSelectedCitation(null)

      const submittedText = lastSubmittedText.current
      const recoveredCompletedTurn = submittedText
        ? hasCompletedPrompt(recovered, submittedText)
        : false
      if (recoveredCompletedTurn) {
        clearError()
        setStreamErrorCode(null)
        setStreamErrorReference(null)
        setFailedPrompt(null)
        lastSubmittedText.current = null
      }
      void onPersisted()
    })
  }, [clearError, error, onPersisted, setMessages, threadId])

  function submitText(text: string) {
    const trimmed = text.trim()
    if (!trimmed || isStreaming) return
    clearError()
    setStreamErrorCode(null)
    setStreamErrorReference(null)
    setFailedPrompt(null)
    lastSubmittedText.current = trimmed
    setInput('')
    void sendMessage({ text: trimmed })
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    submitText(input)
  }

  function retryFailedPrompt() {
    if (failedPrompt) submitText(failedPrompt)
  }

  return (
    <div className="flex h-full min-h-0 flex-col bg-[#f7f8fc]">
      <header className="flex min-h-16 shrink-0 items-center justify-between gap-4 border-b border-slate-200/80 bg-white/85 px-5 py-3 backdrop-blur-xl sm:px-7">
        <div className="min-w-0">
          <h1 className="truncate text-base font-semibold tracking-tight text-slate-950 sm:text-lg">{title}</h1>
          <p className="mt-0.5 text-xs text-slate-500">Private workspace · Saved automatically</p>
        </div>
        <div className="hidden items-center gap-2 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-xs font-medium text-emerald-800 sm:flex">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
          Grounding enforced
        </div>
      </header>

      <div className="relative flex min-h-0 flex-1">
        <div className="research-canvas min-w-0 flex-1 overflow-y-auto px-4 py-8 sm:px-7">
          <div className="mx-auto max-w-4xl space-y-7">
            {messages.length === 0 && (
              <div className="mx-auto max-w-3xl py-8 sm:py-14">
                <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-cyan-400 via-violet-500 to-indigo-700 text-sm font-black text-white shadow-xl shadow-violet-300/30">DC</div>
                <div className="text-center">
                  <p className="mt-5 text-xs font-semibold uppercase tracking-[0.2em] text-violet-700">SEC filing intelligence</p>
                  <h2 className="mt-2 text-3xl font-semibold tracking-[-0.03em] text-slate-950 sm:text-4xl">
                    Start with a research question.
                  </h2>
                  <p className="mx-auto mt-3 max-w-xl text-sm leading-6 text-slate-500 sm:text-base">
                    Compare disclosures, trace changes across years, or verify a specific claim. Every supported answer opens back to its source passage.
                  </p>
                </div>
                <div className="mx-auto mt-8 grid max-w-2xl gap-3 text-left sm:grid-cols-2">
                  {EXAMPLE_QUESTIONS.map((question) => (
                    <button
                      className="group rounded-2xl border border-slate-200/80 bg-white/90 p-4 text-left shadow-sm transition hover:-translate-y-0.5 hover:border-violet-300 hover:shadow-lg hover:shadow-violet-100 focus:outline-none focus:ring-4 focus:ring-violet-100"
                      key={question.text}
                      type="button"
                      onClick={() => setInput(question.text)}
                    >
                      <span className="text-[10px] font-semibold uppercase tracking-[0.16em] text-violet-600">{question.label}</span>
                      <span className="mt-2 block text-sm leading-6 text-slate-700 group-hover:text-slate-950">{question.text}</span>
                    </button>
                  ))}
                </div>
                <div className="mt-7 flex items-center justify-center gap-5 text-xs text-slate-400">
                  <span>25 filings</span><span>•</span><span>2021–2025</span><span>•</span><span>5 companies</span>
                </div>
              </div>
            )}
            {messages.map((message) => {
              if (!hasRenderableContent(message)) return null
              if (message.role === 'assistant') {
                return (
                  <AssistantMessage
                    key={message.id}
                    message={message}
                    selectedPosition={
                      selectedCitation?.messageId === message.id
                        ? selectedCitation.citation.position
                        : null
                    }
                    onSelectCitation={(citation) =>
                      setSelectedCitation({ messageId: message.id, citation })
                    }
                  />
                )
              }
              return (
                <article className="flex items-end justify-end gap-2.5" key={message.id}>
                  <div className="max-w-[82%] whitespace-pre-wrap rounded-2xl rounded-br-md bg-gradient-to-br from-violet-700 to-indigo-700 px-4 py-3 text-sm leading-6 text-white shadow-md shadow-violet-200/50">
                    {messageText(message)}
                  </div>
                  <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-slate-900 text-[10px] font-bold text-white">YOU</span>
                </article>
              )
            })}
            {isStreaming && (
              <div
                className="flex items-center gap-3 rounded-2xl border border-slate-200/80 bg-white/80 px-4 py-3 text-sm text-slate-600 shadow-sm"
                role="status"
                aria-live="polite"
              >
                <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-gradient-to-br from-cyan-400 to-violet-700 text-[9px] font-black text-white">DC</span>
                <span className="flex gap-1" aria-hidden="true">
                  <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-violet-500 [animation-delay:-.3s]" />
                  <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-violet-500 [animation-delay:-.15s]" />
                  <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-violet-500" />
                </span>
                {isDeliveringText
                  ? 'Delivering the cited answer…'
                  : 'Searching filings and checking sources…'}
              </div>
            )}
            {error && (
              <ChatErrorNotice
                error={error}
                streamCode={streamErrorCode}
                streamReference={streamErrorReference}
                canRetry={Boolean(failedPrompt) && !isStreaming}
                onRetry={retryFailedPrompt}
              />
            )}
            <div ref={messagesEnd} />
          </div>
        </div>

        {selectedCitation && (
          <SourcePassagePanel
            citation={selectedCitation.citation}
            onClose={() => setSelectedCitation(null)}
          />
        )}
      </div>

      <div className="shrink-0 bg-gradient-to-t from-white via-white to-white/70 px-4 pb-4 pt-2 sm:px-7 sm:pb-5">
        <form className="mx-auto max-w-4xl rounded-2xl border border-slate-300/90 bg-white p-2 shadow-[0_12px_40px_rgba(15,23,42,0.10)] transition focus-within:border-violet-400 focus-within:ring-4 focus-within:ring-violet-100/70" onSubmit={handleSubmit}>
          <label className="sr-only" htmlFor="chat-message">Message</label>
          <div className="flex items-end gap-2">
            <textarea
              id="chat-message"
              className="max-h-40 min-h-12 flex-1 resize-none bg-transparent px-3 py-3 text-sm leading-6 text-slate-950 outline-none placeholder:text-slate-400 disabled:text-slate-400"
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === 'Enter' && !event.shiftKey) {
                  event.preventDefault()
                  event.currentTarget.form?.requestSubmit()
                }
              }}
              placeholder="Ask a question across the filing corpus…"
              rows={1}
              disabled={isStreaming}
            />
            {isStreaming ? (
              <button className="mb-1 rounded-xl border border-slate-300 px-4 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-50" type="button" onClick={stop}>Stop</button>
            ) : (
              <button
                className="mb-1 flex h-10 min-w-10 items-center justify-center rounded-xl bg-gradient-to-br from-violet-600 to-indigo-700 px-4 text-sm font-semibold text-white shadow-md shadow-violet-200 transition hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:translate-y-0"
                type="submit"
                disabled={!input.trim()}
                aria-label="Send message"
              >
                Ask ↗
              </button>
            )}
          </div>
          <div className="flex items-center justify-between px-3 pb-1 text-[10px] text-slate-400">
            <span>Enter to send · Shift + Enter for a new line</span>
            <span className="hidden sm:inline">Grounded in retrieved SEC filings</span>
          </div>
        </form>
      </div>
    </div>
  )
}

function hasRenderableContent(message: DocumentChatMessage): boolean {
  return Boolean(
    messageText(message) ||
    messageCitations(message).length > 0 ||
    messageAnswerStatus(message),
  )
}

function hasCompletedPrompt(
  messages: DocumentChatMessage[],
  prompt: string,
): boolean {
  const userIndex = messages.findLastIndex(
    (message) => message.role === 'user' && messageText(message).trim() === prompt,
  )
  return (
    userIndex >= 0 &&
    messages.slice(userIndex + 1).some((message) => message.role === 'assistant')
  )
}
