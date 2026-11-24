"use client"

import { useEffect, useState } from "react"
import Link from "next/link"

import { buttonVariants } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { DashboardHeader } from "@/components/dashboard/header"

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"

import { getApiToken } from "@/lib/auth-token"
import {
  listDetections,
  type DetectionWithClosure,
} from "@/lib/api"

export default function Home() {
  const [detections, setDetections] =
    useState<DetectionWithClosure[]>([])

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")

  useEffect(() => {
    let cancelled = false

    async function loadDetections() {
      try {
        const token = await getApiToken()
        const data = await listDetections(token)

        if (!cancelled) {
          setDetections(
            data.filter(
              (detection) => detection.status !== "Closed"
            )
          )
        }
      } catch (error) {
        if (!cancelled) {
          setError(
            "Unable to load detections. Please try again."
          )
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    loadDetections()

    return () => {
      cancelled = true
    }
  }, [])

  return (
    <main className="min-h-screen bg-slate-50">
      <DashboardHeader />

      <div className="mx-auto max-w-6xl px-8 py-10">
        <div className="mb-8">
          <h2 className="text-3xl font-bold tracking-tight text-slate-900">
            Active detections
          </h2>

          <p className="mt-2 text-slate-500">
            Wildfire detections currently requiring attention.
          </p>
        </div>

        {/* TODO: Implement real new detection notifications. */}

        {loading ? (
          <p className="text-sm text-slate-500">
            Loading detections...
          </p>
        ) : error ? (
          <div className="rounded-xl border border-red-200 bg-red-50 p-4">
            <p className="text-sm text-red-700">
              {error}
            </p>
          </div>
        ) : detections.length === 0 ? (
          <div className="rounded-xl border bg-white p-10 text-center">
            <h3 className="text-lg font-semibold text-slate-900">
              No active detections
            </h3>

            <p className="mt-2 text-sm text-slate-500">
              Refresh the page to check for new detections.
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {detections.map((detection) => (
              <Card key={detection.id}>
                <CardHeader>
                  <div className="flex items-center justify-between gap-4">
                    <CardTitle className="break-all text-lg">
                      {detection.id}
                    </CardTitle>

                    {detection.status === "Open" ? (
                      <Badge variant="destructive">
                        Open
                      </Badge>
                    ) : (
                      <Badge
                        variant="outline"
                        className="border-green-200 bg-green-50 text-green-700"
                      >
                        Verified
                      </Badge>
                    )}
                  </div>
                </CardHeader>

                <CardContent>
                  <div className="grid gap-6 md:grid-cols-[1fr_auto] md:items-end">
                    <div className="grid gap-4 sm:grid-cols-3">
                      <div>
                        <p className="text-sm text-slate-500">
                          Time
                        </p>

                        <p className="mt-1 font-medium text-slate-900">
                          {new Date(
                            detection.timestamp
                          ).toLocaleTimeString([], {
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </p>
                      </div>

                      <div>
                        <p className="text-sm text-slate-500">
                          Confidence
                        </p>

                        <p className="mt-1 font-medium text-slate-900">
                          {detection.confidence}%
                        </p>
                      </div>

                      <div>
                        <p className="text-sm text-slate-500">
                          Coordinates
                        </p>

                        <p className="mt-1 font-medium text-slate-900">
                          {detection.latitude}, {detection.longitude}
                        </p>
                      </div>
                    </div>

                    <Link
                      href={`/detections/${encodeURIComponent(detection.id)}`}
                      className={buttonVariants()}
                      style={{
                        backgroundColor: "#FF6B0B",
                        color: "white",
                      }}
                    >
                      Open details
                    </Link>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </main>
  )
}