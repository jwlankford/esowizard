import type { Answer, CategoryInfo } from "../types/api";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`/api/v1${path}`, options);
  if (!response.ok) {
    throw new Error(
      `Request failed (${response.status}). Check the API and its configuration.`,
    );
  }
  return response.json() as Promise<T>;
}

export function getCategories(): Promise<CategoryInfo[]> {
  return request("/categories");
}

export async function askQuestion(
  question: string,
  category: string | null,
): Promise<Answer> {
  const response = await fetch("/api/v1/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, category }),
  });
  // The API reports provider/database failures as a structured "error" answer.
  const body = (await response.json().catch(() => null)) as Answer | null;
  if (body && typeof body.status === "string") {
    return body;
  }
  throw new Error(
    `Request failed (${response.status}). Check the API and its configuration.`,
  );
}
