"use client"

import type { ReactNode } from "react"
import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { getCurrentUser } from "aws-amplify/auth"

export function AuthGuard({
  children,
}: {
  children: ReactNode
}) {
  const router = useRouter()
  const [checking, setChecking] = useState(true)

  useEffect(() => {
    async function checkAuth() {
      try {
        await getCurrentUser()
        setChecking(false)
      } catch {
        router.replace("/login")
      }
    }

    checkAuth()
  }, [router])

  if (checking) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-50">
        <p className="text-sm text-slate-500">
          Checking session...
        </p>
      </main>
    )
  }

  return <>{children}</>
}