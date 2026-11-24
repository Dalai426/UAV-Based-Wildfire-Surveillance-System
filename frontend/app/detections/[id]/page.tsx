"use client"

import { useEffect, useState } from "react"
import { useParams } from "next/navigation"
import Link from "next/link"

import { Badge } from "@/components/ui/badge"
import { DashboardHeader } from "@/components/dashboard/header"
import { DetectionInfo } from "@/components/dashboard/detection-info"

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"

import { getApiToken } from "@/lib/auth-token"
import { getDetection, ApiError } from "@/lib/api"

type DetectionItem = Awaited<ReturnType<typeof getDetection>>

export default function DetectionPage() {
  const { id } = useParams<{ id: string }>()

  const [detection, setDetection] =
    useState<DetectionItem | null>(null)

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")

  useEffect(() => {
    let cancelled = false

    async function loadDetection() {
      setLoading(true)
      setError("")
      setDetection(null)

      try {
        const token = await getApiToken()
        const data = await getDetection(id, token)

        if (!cancelled) {
          setDetection(data)
        }
      } catch (error) {
        if (!cancelled) {
          if (error instanceof ApiError && error.status === 404) {
            setError("Detection not found")
          } else {
            setError("Unable to load detection")
          }
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    loadDetection()

    return () => {
      cancelled = true
    }
  }, [id])

  if (loading) {
    return (
      <main className="min-h-screen bg-slate-50">
        <DashboardHeader />

        <div className="mx-auto max-w-6xl px-8 py-10">
          <p className="text-sm text-slate-500">
            Loading detection...
          </p>
        </div>
      </main>
    )
  }

  if (!detection || error) {
    return (
      <main className="min-h-screen bg-slate-50 p-8">
        <div className="mx-auto max-w-5xl">
          <h1 className="text-2xl font-bold">
            {error || "Detection not found"}
          </h1>

          <Link
            href="/detections"
            className="text-sm text-slate-500 hover:text-slate-900"
          >
            Back to detections
          </Link>
        </div>
      </main>
    )
  }

  return (
    <main className="min-h-screen bg-slate-50">
      <DashboardHeader />

      <div className="mx-auto max-w-6xl px-8 py-10">

        <Link
          href="/detections"
          className="text-sm text-slate-500 hover:text-slate-900"
        >
          ← Back to detections
        </Link>

        <div className="mt-6 flex items-center justify-between gap-4">
          <div className="min-w-0">
            <h2 className="break-words text-3xl font-bold">
              Detection {detection.id}
            </h2>

            <p className="mt-2 text-slate-500">
              Wildfire detection details
            </p>
          </div>

          {detection.status === "Open" ? (
            <Badge variant="destructive">
              Open
            </Badge>
          ) : (
            <Badge
              variant="outline"
              className="border-green-200 bg-green-50 text-green-700"
            >
              {detection.status}
            </Badge>
          )}
        </div>

        <Card className="mt-8">
          <CardHeader>
            <CardTitle>
              Detection footage
            </CardTitle>
          </CardHeader>

          <CardContent>
            <div className="flex aspect-video items-center justify-center rounded-xl bg-slate-900 text-white">
              Video will appear here
            </div>
          </CardContent>
        </Card>

        <DetectionInfo
          key={detection.id}
          id={detection.id}
          timestamp={detection.timestamp}
          confidence={detection.confidence}
          latitude={detection.latitude}
          longitude={detection.longitude}
          initialStatus={detection.status}
          onStatusChange={(newStatus) =>
            setDetection((previous) =>
              previous
                ? { ...previous, status: newStatus }
                : null
            )
          }
        />
      </div>
    </main>
  )
}