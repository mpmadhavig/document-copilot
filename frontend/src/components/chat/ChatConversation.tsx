import { useEffect, useMemo, useRef, useState, type FormEvent } from 'react'
import { useChat } from '@ai-sdk/react'
import { DefaultChatTransport, type UIMessage } from 'ai'

import { api } from '@/lib/api'
import { env } from '@/lib/env'
import { getAccessToken } from '@/lib/supabase'

type ChatConversationProps = {
  threadId: string
  title: string
  initialMessages: UIMessage[]
  onPersisted: () => Promise<void>
}

function messageText(message: UIMessage): string {
  return message.parts
    .filter((part) => part.type === 'text')
    .map((part) => part.text)
    .join('')
}

export function ChatConversation({
  threadId,
  title,
  initialMessages,
  onPersisted,
}: ChatConversationProps) {
  const [input, setInput] = useState('')
  const recoveredError = useRef<Error | null>(null)
  const messagesEnd = useRef<HTMLDivElement | null>(null)
  const transport = useMemo(
    () =>
      new DefaultChatTransport({
        api: `${env.apiBaseUrl}/chat/stream`,
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
  } = useChat({
    id: threadId,
    messages: initialMessages,
    transport,
    onFinish: ({ isError }) => {
      if (!isError) void onPersisted()
    },
  })

  const isStreaming = status === 'submitted' || status === 'streaming'

  useEffect(() => {
    messagesEnd.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, status])

  useEffect(() => {
    if (!error || recoveredError.current === error) return
    recoveredError.current = error
    void api.getMessages(threadId).then((stored) => {
      setMessages(
        stored.map(({ id, role, parts }) => ({ id, role, parts }) as UIMessage),
      )
      void onPersisted()
    })
  }, [error, onPersisted, setMessages, threadId])

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const text = input.trim()
    if (!text || isStreaming) return
    clearError()
    setInput('')
    void sendMessage({ text })
  }

  return (
    <div className="flex h-svh min-h-0 flex-col">
      <header className="border-b border-slate-200 bg-white px-6 py-4">
        <h1 className="truncate text-lg font-semibold text-slate-950">{title}</h1>
      </header>

      <div className="min-h-0 flex-1 overflow-y-auto px-6 py-8">
        <div className="mx-auto max-w-3xl space-y-6">
          {messages.length === 0 && (
            <div className="py-20 text-center">
              <h2 className="text-2xl font-semibold text-slate-900">What would you like to research?</h2>
              <p className="mt-3 text-slate-500">Ask a question to test the streaming chat connection.</p>
            </div>
          )}
          {messages.map((message) => (
            <article
              className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
              key={message.id}
            >
              <div
                className={`max-w-[85%] whitespace-pre-wrap rounded-2xl px-4 py-3 text-sm leading-6 ${
                  message.role === 'user'
                    ? 'bg-violet-700 text-white'
                    : 'border border-slate-200 bg-white text-slate-800 shadow-sm'
                }`}
              >
                {messageText(message)}
              </div>
            </article>
          ))}
          {isStreaming && (
            <p className="text-sm text-slate-500" role="status">
              {status === 'submitted' ? 'Thinking…' : 'Responding…'}
            </p>
          )}
          {error && (
            <p className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700" role="alert">
              {error.message || 'The response could not be completed. Please try again.'}
            </p>
          )}
          <div ref={messagesEnd} />
        </div>
      </div>

      <div className="border-t border-slate-200 bg-white px-6 py-4">
        <form className="mx-auto flex max-w-3xl gap-3" onSubmit={handleSubmit}>
          <label className="sr-only" htmlFor="chat-message">Message</label>
          <textarea
            id="chat-message"
            className="min-h-12 flex-1 resize-none rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-950 outline-none transition focus:border-violet-600 focus:ring-2 focus:ring-violet-100 disabled:bg-slate-50"
            value={input}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault()
                event.currentTarget.form?.requestSubmit()
              }
            }}
            placeholder="Ask about the filing corpus…"
            rows={1}
            disabled={isStreaming}
          />
          {isStreaming ? (
            <button
              className="rounded-xl border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
              type="button"
              onClick={stop}
            >
              Stop
            </button>
          ) : (
            <button
              className="rounded-xl bg-violet-700 px-5 py-2 text-sm font-semibold text-white transition hover:bg-violet-800 disabled:cursor-not-allowed disabled:opacity-50"
              type="submit"
              disabled={!input.trim()}
            >
              Send
            </button>
          )}
        </form>
      </div>
    </div>
  )
}
