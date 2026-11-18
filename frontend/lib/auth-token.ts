import { fetchAuthSession } from "aws-amplify/auth"

export async function getApiToken(): Promise<string> {
  const session = await fetchAuthSession()

  const token = session.tokens?.idToken?.toString()

  if (!token) {
    throw new Error("No Cognito ID token available.")
  }

  return token
}