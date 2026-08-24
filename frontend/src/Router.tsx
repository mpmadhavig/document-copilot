import { Navigate, Route, Routes } from 'react-router-dom'

import { ProtectedRoute } from './components/auth/ProtectedRoute'
import { ChatLayout } from './components/chat/ChatLayout'
import { ChatIndexPage } from './pages/chat/ChatIndexPage'
import { ChatThreadPage } from './pages/chat/ChatThreadPage'
import { SignInPage } from './pages/auth/SignInPage'
import { SignUpPage } from './pages/auth/SignUpPage'

export function Router() {
  return (
    <Routes>
      <Route path="/signin" element={<SignInPage />} />
      <Route path="/signup" element={<SignUpPage />} />
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
