import { useEffect, useState } from 'react'
import { Navigate, Outlet, useLocation } from 'react-router-dom'
import type { Session } from '@supabase/supabase-js'

import { supabase } from '../../lib/supabase'

export function ProtectedRoute() {
  const location = useLocation()
  const [session, setSession] = useState<Session | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    let isMounted = true

    void supabase.auth.getSession().then(({ data }) => {
      if (!isMounted) return
      setSession(data.session)
      setIsLoading(false)
    })

    const { data } = supabase.auth.onAuthStateChange((_event, nextSession) => {
      setSession(nextSession)
      setIsLoading(false)
    })

    return () => {
      isMounted = false
      data.subscription.unsubscribe()
    }
  }, [])

  if (isLoading) {
    return (
      <main className="flex min-h-svh items-center justify-center bg-slate-50">
        <p className="text-sm text-slate-600" role="status">
          Loading your session…
        </p>
      </main>
    )
  }

  if (!session) {
    return <Navigate to="/signin" state={{ from: location }} replace />
  }

  return <Outlet />
}
