"use client"

import { useEffect, useState } from "react"

import { getApiToken } from "@/lib/auth-token"
import {
  listDetections,
  type DetectionWithClosure,
} from "@/lib/api"

export default function ApiTestPage() {
  const [detections, setDetections] =
    useState<DetectionWithClosure[]>([])

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")

  useEffect(() => {
    async function load() {
      try {
        const token = await getApiToken()
        const data = await listDetections(token)

        setDetections(data)
      } catch (error) {
        console.error(error)

        if (error instanceof Error) {
          setError(error.message)
        } else {
          setError("Unknown error")
        }
      } finally {
        setLoading(false)
      }
    }

    load()
  }, [])

  if (loading) {
    return <p className="p-8">Loading API...</p>
  }

  if (error) {
    return (
      <div className="p-8">
        <h1 className="font-semibold">API error</h1>
        <p className="mt-2 text-red-600">{error}</p>
      </div>
    )
  }

  return (
    <div className="p-8">
      <h1 className="text-xl font-semibold">
        API test
      </h1>

      <p className="mt-2">
        Incidents received: {detections.length}
      </p>

      <pre className="mt-6 overflow-auto rounded-lg bg-slate-100 p-4 text-sm">
        {JSON.stringify(detections, null, 2)}
      </pre>
    </div>
  )
}