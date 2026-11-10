export interface Source {
  title: string;
  source_name: string;
  source_url: string;
  chunk_number: number;
  content: string;
}

export interface Answer {
  answer: string;
  sources: Source[];
}
