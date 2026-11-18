import { ApiError } from "./api"

export function getApiErrorMessage(error: unknown): string {
  if (!(error instanceof ApiError)) {
    return "Something went wrong. Please try again."
  }

  switch (error.status) {
    case 400:
      return "The request contains invalid data."

    case 404:
      return "The incident could not be found."

    case 409:
      return error.message || "The incident has already been updated."

    case 500:
      return "The server encountered an error. Please try again."

    default:
      return error.message || "Something went wrong."
  }
}