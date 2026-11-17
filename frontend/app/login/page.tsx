"use client"

import { FormEvent, useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { getCurrentUser, signIn } from "aws-amplify/auth"

export default function LoginPage() {
  const router = useRouter()
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    async function checkExistingSession() {
      try {
        await getCurrentUser()
        router.replace("/detections")
      } catch {
      }
    }

    checkExistingSession()
  }, [router])

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    if (!email || !password) {
      setError("Please enter your email and password.")
      return
    }

    setError("")
    setLoading(true)

    try {
      const result = await signIn({
        username: email.trim(),
        password,
      })

      if (result.nextStep.signInStep === "DONE") {
        router.replace("/detections")
        return
      }

      if (
        result.nextStep.signInStep ===
        "CONFIRM_SIGN_IN_WITH_NEW_PASSWORD_REQUIRED"
      ) {
        setError(
          "You must set a new password before signing in."
        )
        return
      }

      setError(
        `Additional sign-in step required: ${result.nextStep.signInStep}`
      )
    } catch (error) {
      console.error("Cognito sign-in error:", error)

      setError("Incorrect email or password.")
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 px-6">
      <div className="w-full max-w-md">
        <div className="mb-8 flex items-center justify-center gap-3">
          <div className="h-9 w-1 rounded-full bg-[#FF6B0B]" />

        <h1 className="text-3xl font-semibold text-[#172033]">
          Wildfire Monitor
        </h1>
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="text-2xl">
              Sign in
            </CardTitle>
          </CardHeader>

          <CardContent>
            <form
              onSubmit={handleSubmit}
              className="space-y-5"
            >
                <div className="space-y-2">
                <Label htmlFor="email">
                  Email
                </Label>

                <Input
                  id="email"
                  type="text"
                  placeholder="Enter your email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                />
                </div>

              <div className="space-y-2">
                <Label htmlFor="password">
                  Password
                </Label>

                <Input
                  id="password"
                  type="password"
                  placeholder="Enter your password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                />
              </div>

              {error && (
                <p className="text-sm text-red-600">
                  {error}
                </p>
              )}

              <Button
                type="submit"
                disabled={loading}
                className="h-11 w-full"
                style={{
                  backgroundColor: "#FF6B0B",
                  color: "white",
                }}
              >
                {loading ? "Signing in..." : "Sign in"}
              </Button>

            </form>
          </CardContent>
        </Card>

      </div>
    </main>
  )
}