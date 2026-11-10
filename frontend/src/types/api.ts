export interface CategoryInfo {
  value: string;
  label: string;
}

export interface SourceRef {
  title: string;
  url: string | null;
  source_name: string;
}

export type AskStatus = "answered" | "insufficient_knowledge" | "error";

export interface Answer {
  question: string;
  answer: string;
  category: string | null;
  status: AskStatus;
  sources: SourceRef[];
  related_queries: string[];
}
