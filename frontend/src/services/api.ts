import type { Answer } from "../types/api";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`/api/v1${path}`, options);
  if (!response.ok) {
    throw new Error(
      `Request failed (${response.status}). Check the API and its configuration.`,
    );
  }
  return response.json() as Promise<T>;
}

export function getCategories(): Promise<string[]> {
  return request("/categories");
}

export function askQuestion(
  question: string,
  category: string | null,
): Promise<Answer> {
  return request("/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, category }),
  });
}
