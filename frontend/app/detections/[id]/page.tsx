import Link from "next/link"
import { Badge } from "@/components/ui/badge"
import { detections } from "@/lib/mock-data"
import { DashboardHeader } from "@/components/dashboard/header"
import { DetectionInfo } from "@/components/dashboard/detection-info"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"

export const instant = false
export default async function DetectionPage({
  params,
}: {
  params: Promise<{ id: string }>
}) {
  const { id } = await params

  const detection = detections.find(
    (detection) => detection.id === id
  )

  if (!detection) {
    return (
      <main className="min-h-screen bg-slate-50 p-8">
        <div className="mx-auto max-w-5xl">
          <h1 className="text-2xl font-bold">
            Detection not found
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

        <div className="mt-6 flex items-center justify-between">
          <div>
            <h2 className="text-3xl font-bold">
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
              Verified
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
        id={detection.id}
        timestamp={detection.timestamp}
        confidence={detection.confidence}
        latitude={detection.latitude}
        longitude={detection.longitude}
        initialStatus={detection.status}
        />
      </div>
    </main>
  )
}