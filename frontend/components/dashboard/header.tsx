"use client"

import { CircleUserRound } from "lucide-react"
import { useRouter } from "next/navigation"
import { signOut } from "aws-amplify/auth"

export function DashboardHeader() {
  const router = useRouter()

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
            size={40}
            strokeWidth={1.8}
            className="text-[#64748B]"
          />

          <button
            onClick={handleLogout}
            className="text-sm font-medium text-slate-500 transition-colors hover:text-[#FF6B0B]"
          >
            Log out
          </button>
        </div>
      </div>
    </header>
  )
}