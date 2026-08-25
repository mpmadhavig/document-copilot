import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import './index.css'
import { FrontendErrorBoundary } from './components/FrontendErrorBoundary.tsx'
import { installGlobalErrorLogging } from './lib/clientLogger.ts'
import { Router } from './Router.tsx'

installGlobalErrorLogging()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <FrontendErrorBoundary>
      <BrowserRouter>
        <Router />
      </BrowserRouter>
    </FrontendErrorBoundary>
  </StrictMode>,
)
