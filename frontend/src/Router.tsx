import { Navigate, Route, Routes } from 'react-router-dom'

import { ProtectedRoute } from './components/auth/ProtectedRoute'
import { ChatLayout } from './components/chat/ChatLayout'
import { ChatIndexPage } from './pages/chat/ChatIndexPage'
import { ChatThreadPage } from './pages/chat/ChatThreadPage'
import { AuthPage } from './pages/auth/AuthPage'

export function Router() {
  return (
    <Routes>
      <Route path="/signin" element={<AuthPage key="signin" initialMode="signin" />} />
      <Route path="/signup" element={<AuthPage key="signup" initialMode="signup" />} />
      <Route element={<ProtectedRoute />}>
        <Route path="/" element={<Navigate to="/chats" replace />} />
        <Route path="/chats" element={<ChatLayout />}>
          <Route index element={<ChatIndexPage />} />
          <Route path=":threadId" element={<ChatThreadPage />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/signin" replace />} />
    </Routes>
  )
}
