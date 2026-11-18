"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { CircleUserRound } from "lucide-react"
import {
  fetchUserAttributes,
  signOut,
} from "aws-amplify/auth"

export function DashboardHeader() {
  const router = useRouter()
  const [email, setEmail] = useState<string>("")

  useEffect(() => {
    async function loadUserEmail() {
      try {
        const attributes = await fetchUserAttributes()

        setEmail(attributes.email ?? "")
      } catch (error) {
        console.error("Error loading user attributes:", error)
      }
    }

    loadUserEmail()
  }, [])

  async function handleLogout() {
    try {
      await signOut()
      router.replace("/login")
      router.refresh()
    } catch (error) {
      console.error("Error signing out:", error)
    }
  }

  return (
    <header className="w-full border-b border-[#E2E8F0] bg-white">
      <div className="mx-auto flex w-full max-w-6xl items-center justify-between px-8 py-5">
        <div className="flex items-center gap-3">
          <div className="h-8 w-1 rounded-full bg-[#FF6B0B]" />

          <h1 className="text-xl font-semibold text-[#172033]">
            Wildfire Monitor
          </h1>
        </div>

        <div className="flex items-center gap-4">
          <CircleUserRound
            size={36}
            strokeWidth={1.8}
            className="text-[#64748B]"
          />

          {email && (
            <span className="text-sm text-[#64748B]">
              {email}
            </span>
          )}

          <button
            onClick={handleLogout}
            className="text-sm font-medium text-[#64748B] transition-colors hover:text-[#FF6B0B]"
          >
            Log out
          </button>
        </div>
      </div>
    </header>
  )
}