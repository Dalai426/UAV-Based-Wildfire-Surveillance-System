import type { Detection } from "./mock-data"

// Base address of the dashboard API, for example
// https://xxxx.execute-api.eu-north-1.amazonaws.com/prod
// Put it in frontend/.env.local as NEXT_PUBLIC_API_URL (that file is not committed).
const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "").replace(/\/+$/, "")

// What the backend returns for one incident
type ApiIncident = {
  gs_event_id: string
  detection_time: string
  confidence_percent: number
  coordinates: { latitude: number; longitude: number }
  status: "active" | "verified" | "closed"
  closed_by: string | null
  closed_at: string | null
}

// The page's Detection type, plus who closed it and when
export type DetectionWithClosure = Detection & {
  closedBy: string | null
  closedAt: string | null
}

const STATUS: Record<ApiIncident["status"], Detection["status"]> = {
  active: "Open",
  verified: "Verified",
  closed: "Closed",
}

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

export function toDetection(i: ApiIncident): DetectionWithClosure {
  return {
    id: i.gs_event_id,
    timestamp: i.detection_time,
    confidence: i.confidence_percent,
    latitude: i.coordinates.latitude,
    longitude: i.coordinates.longitude,
    status: STATUS[i.status],
    closedBy: i.closed_by,
    closedAt: i.closed_at,
  }
}

// token = the Cognito ID token. The backend expects it as it is,
// in the Authorization header, without the word Bearer.
async function request<T>(path: string, token: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", Authorization: token },
  })
  let body: { success?: boolean; data?: T; error?: string; message?: string } = {}
  try {
    body = await res.json()
  } catch {
    // empty or non-JSON answer
  }
  if (!res.ok) {
    throw new ApiError(res.status, body.error ?? body.message ?? `Request failed (${res.status})`)
  }
  return body.data as T
}

const enc = encodeURIComponent

export async function listDetections(token: string): Promise<DetectionWithClosure[]> {
  const items = await request<ApiIncident[]>("/incidents", token)
  return items.map(toDetection)
}

export async function getDetection(id: string, token: string): Promise<DetectionWithClosure> {
  return toDetection(await request<ApiIncident>(`/incidents/${enc(id)}`, token))
}

// Open -> Verified
export async function verifyDetection(id: string, token: string): Promise<Detection["status"]> {
  await request(`/incidents/${enc(id)}/verify`, token, { method: "POST" })
  return "Verified"
}

// Verified (or Open) -> Closed. The backend takes the name from the token.
export async function closeDetection(
  id: string,
  token: string
): Promise<{ closedBy: string; closedAt: string }> {
  const r = await request<{ closed_by: string; closed_at: string }>(
    `/incidents/${enc(id)}/close`,
    token,
    { method: "POST", body: "{}" }
  )
  return { closedBy: r.closed_by, closedAt: r.closed_at }
}
