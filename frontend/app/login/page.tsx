"use client"

import { FormEvent, useState } from "react"
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

export default function LoginPage() {
  const router = useRouter()
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState("")

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    if (!username || !password) {
      setError("Please enter your username and password.")
      return
    }

    setError("")

    router.push("/detections")
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
                <Label htmlFor="username">
                  Username
                </Label>

                <Input
                  id="username"
                  type="text"
                  placeholder="Enter your username"
                  value={username}
                  onChange={(event) => setUsername(event.target.value)}
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
                className="h-11 w-full"
                style={{
                  backgroundColor: "#FF6B0B",
                  color: "white",
                }}
              >
                Sign in
              </Button>

            </form>
          </CardContent>
        </Card>

      </div>
    </main>
  )
}