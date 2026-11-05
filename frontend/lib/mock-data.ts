export type Detection = {
  id: string
  timestamp: string
  confidence: number
  latitude: number
  longitude: number
  status: "Open" | "Verified" | "Closed"
}

export const detections: Detection[] = [
  {
    id: "INC-204",
    timestamp: "2026-10-31T08:40:31Z",
    confidence: 93,
    latitude: 55.6759,
    longitude: 12.5655,
    status: "Verified",
  },
  {
    id: "INC-203",
    timestamp: "2026-10-31T04:20:10Z",
    confidence: 88,
    latitude: 55.6759,
    longitude: 12.5655,
    status: "Verified",
  },
]