"use client"

import { useState } from "react"

import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog"

type DetectionInfoProps = {
  id: string
  timestamp: string
  confidence: number
  latitude: number
  longitude: number
  initialStatus: "Open" | "Verified" | "Closed"
}

export function DetectionInfo({
  id,
  timestamp,
  confidence,
  latitude,
  longitude,
  initialStatus,
}: DetectionInfoProps) {
  const [status, setStatus] = useState(initialStatus)

  return (
    <div className="mt-6 grid gap-6 md:grid-cols-2">

      <Card>
        <CardHeader>
          <CardTitle className="text-base">
            Detection data
          </CardTitle>
        </CardHeader>

        <CardContent className="space-y-4">
          <div>
            <p className="text-sm text-slate-500">
              Timestamp
            </p>

            <p className="font-medium text-slate-900">
              {new Date(timestamp).toLocaleString("en-GB", {
                day: "2-digit",
                month: "2-digit",
                year: "numeric",
                hour: "2-digit",
                minute: "2-digit",
                second: "2-digit",
              })}
            </p>
          </div>

          <div>
            <p className="text-sm text-slate-500">
              Confidence
            </p>

            <p className="font-medium text-slate-900">
              {confidence}%
            </p>
          </div>

          <div>
            <p className="text-sm text-slate-500">
              Status
            </p>

            <p className="font-medium text-slate-900">
              {status}
            </p>
          </div>

          <div>
            <p className="text-sm text-slate-500">
              Record ID
            </p>

            <p className="font-medium text-slate-900">
              {id}
            </p>
          </div>
        </CardContent>
      </Card>

      <div className="flex flex-col">

        <Card>
          <CardHeader>
            <CardTitle className="text-base">
              Coordinates
            </CardTitle>
          </CardHeader>

          <CardContent className="space-y-4">
            <div>
              <p className="text-sm text-slate-500">
                Latitude
              </p>

              <p className="font-medium text-slate-900">
                {latitude}
              </p>
            </div>

            <div>
              <p className="text-sm text-slate-500">
                Longitude
              </p>

              <p className="font-medium text-slate-900">
                {longitude}
              </p>
            </div>
          </CardContent>
        </Card>

        {status === "Verified" && (
          <div className="mt-8 flex justify-center">
            <AlertDialog>

              <AlertDialogTrigger
                render={
                  <Button className="h-12 min-w-52 rounded-xl bg-orange-500 px-12 text-base hover:bg-orange-600" />
                }
              >
                Close incident
              </AlertDialogTrigger>

              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>
                    Close this incident?
                  </AlertDialogTitle>

                  <AlertDialogDescription>
                    This will mark the verified wildfire incident as closed.
                  </AlertDialogDescription>
                </AlertDialogHeader>

                <AlertDialogFooter>
                  <AlertDialogCancel>
                    Cancel
                  </AlertDialogCancel>

                  <AlertDialogAction
                    onClick={() => setStatus("Closed")}
                    className="bg-orange-500 hover:bg-orange-600"
                  >
                    Close incident
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>

            </AlertDialog>
          </div>
        )}

        {status === "Closed" && (
          <div className="mt-8 rounded-xl border border-green-200 bg-green-50 px-6 py-3 text-center text-sm font-medium text-green-700">
            Incident closed
          </div>
        )}

      </div>
    </div>
  )
}