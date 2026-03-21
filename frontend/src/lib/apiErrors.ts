export function hasApiResponse(error: unknown): boolean {
  return typeof error === "object" && error !== null && "response" in error;
}
