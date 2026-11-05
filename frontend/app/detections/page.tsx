import Link from "next/link"
import { buttonVariants } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { detections } from "@/lib/mock-data"
import { DashboardHeader } from "@/components/dashboard/header"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"

export default function Home() {
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

        <div className="mb-8 rounded-xl border border-orange-200 bg-orange-50 p-4">
          <div className="flex items-start gap-3">
            <div className="mt-1 h-2.5 w-2.5 rounded-full bg-red-500" />

            <div>
              <p className="font-medium text-slate-900">
                New detection received
              </p>

              <p className="mt-1 text-sm text-slate-600">
                Detection INC-204 has been registered and is now available for review.
              </p>
            </div>
          </div>
        </div>

{detections.length === 0 ? (
  <div className="rounded-xl border bg-white p-10 text-center">
    <h3 className="text-lg font-semibold text-slate-900">
      No active detections
    </h3>

    <p className="mt-2 text-sm text-slate-500">
      New wildfire detections will appear here automatically.
    </p>
  </div>
) : (
  <div className="space-y-4">
    {detections.map((detection) => (
      <Card key={detection.id}>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg">
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
                  {new Date(detection.timestamp).toLocaleTimeString([], {
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
              href={`/detections/${detection.id}`}
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