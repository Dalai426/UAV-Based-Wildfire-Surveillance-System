import { AuthGuard } from "@/components/auth-guard"

export default function DetectionsLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <AuthGuard>
      {children}
    </AuthGuard>
  )
}