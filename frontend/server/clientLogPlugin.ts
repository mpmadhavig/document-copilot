import { Buffer } from 'node:buffer'
import { appendFile, mkdir, rename, rm, stat } from 'node:fs/promises'
import type { IncomingMessage, ServerResponse } from 'node:http'
import { fileURLToPath } from 'node:url'

import type { Plugin } from 'vite'

const ENDPOINT = '/__client-log'
const LOG_PATH = fileURLToPath(new URL('../logs/frontend.log', import.meta.url))
const MAX_BODY_BYTES = 32 * 1024
const MAX_LOG_BYTES = 5 * 1024 * 1024
const BACKUP_COUNT = 5

type MiddlewareServer = {
  middlewares: {
    use(handler: (request: IncomingMessage, response: ServerResponse, next: () => void) => void): void
  }
}

export function clientLogPlugin(): Plugin {
  let writes = Promise.resolve()

  function install(server: MiddlewareServer) {
    server.middlewares.use((request, response, next) => {
      const path = request.url?.split('?', 1)[0]
      if (path !== ENDPOINT) {
        next()
        return
      }
      if (request.method !== 'POST') {
        response.writeHead(405).end()
        return
      }
      if (request.headers['sec-fetch-site'] === 'cross-site') {
        response.writeHead(403).end()
        return
      }

      void readReport(request)
        .then((report) => {
          writes = writes.then(() => writeReport(report))
          return writes
        })
        .then(() => response.writeHead(204).end())
        .catch((error: unknown) => {
          console.error('Unable to write frontend client log', error)
          response.writeHead(400).end()
        })
    })
  }

  return {
    name: 'document-copilot-client-logs',
    configureServer: install,
    configurePreviewServer: install,
  }
}

async function readReport(request: IncomingMessage): Promise<Record<string, string>> {
  const chunks: Buffer[] = []
  let size = 0
  for await (const chunk of request) {
    const buffer = Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk)
    size += buffer.length
    if (size > MAX_BODY_BYTES) throw new Error('client log report is too large')
    chunks.push(buffer)
  }

  const value: unknown = JSON.parse(Buffer.concat(chunks).toString('utf8'))
  if (!isRecord(value)) throw new Error('client log report must be an object')

  const reference = text(value.reference, 64)
  if (!/^fe-[a-z0-9-]+$/.test(reference)) {
    throw new Error('client log reference is invalid')
  }
  return {
    timestamp: new Date().toISOString(),
    reference,
    area: text(value.area, 80),
    action: text(value.action, 160),
    errorName: text(value.errorName, 120),
    message: text(value.message, 2000),
    stack: text(value.stack, 8000),
    route: text(value.route, 500),
    userAgent: text(value.userAgent, 500),
    backendReference: text(value.backendReference, 64),
  }
}

async function writeReport(report: Record<string, string>): Promise<void> {
  await mkdir(new URL('../logs/', import.meta.url), { recursive: true })
  if (await exceedsLimit()) await rotateLogs()
  await appendFile(LOG_PATH, `${JSON.stringify(report)}\n`, 'utf8')
  console.error(JSON.stringify({ service: 'frontend', ...report }))
}

async function exceedsLimit(): Promise<boolean> {
  try {
    return (await stat(LOG_PATH)).size >= MAX_LOG_BYTES
  } catch (error: unknown) {
    if (isNodeError(error) && error.code === 'ENOENT') return false
    throw error
  }
}

async function rotateLogs(): Promise<void> {
  await rm(`${LOG_PATH}.${BACKUP_COUNT}`, { force: true })
  for (let index = BACKUP_COUNT - 1; index >= 1; index -= 1) {
    await renameIfPresent(`${LOG_PATH}.${index}`, `${LOG_PATH}.${index + 1}`)
  }
  await renameIfPresent(LOG_PATH, `${LOG_PATH}.1`)
}

async function renameIfPresent(source: string, destination: string): Promise<void> {
  try {
    await rename(source, destination)
  } catch (error: unknown) {
    if (!isNodeError(error) || error.code !== 'ENOENT') throw error
  }
}

function text(value: unknown, maxLength: number): string {
  return typeof value === 'string' ? value.slice(0, maxLength) : ''
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function isNodeError(value: unknown): value is NodeJS.ErrnoException {
  return value instanceof Error && 'code' in value
}
