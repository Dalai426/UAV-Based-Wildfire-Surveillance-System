import type { ReactNode } from "react"
import { AuthGuard } from "@/components/auth-guard"

export const instant = false

export default function DetectionsLayout({
  children,
}: {
  children: ReactNode
}) {
  return (
    <AuthGuard>
      {children}
    </AuthGuard>
  )
}