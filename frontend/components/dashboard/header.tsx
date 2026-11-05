import { CircleUserRound } from "lucide-react"

export function DashboardHeader() {
  return (
    <header className="w-full border-b border-[#E2E8F0] bg-white">
    <div className="mx-auto flex w-full max-w-6xl items-center justify-between px-8 py-5">
        <div className="flex items-center gap-3">
        <div className="h-8 w-1 rounded-full bg-[#FF6B0B]" />

        <h1 className="text-xl font-semibold text-[#172033]">
            Wildfire Monitor
        </h1>
        </div>

        <CircleUserRound
        size={44}
        strokeWidth={1.8}
        className="text-[#64748B]"
        />
    </div>
    </header>
  )
}