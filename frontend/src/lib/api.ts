export type MetaFilters = {
  grade?: string;
  source?: string;
};

export type SearchRequest = {
  query: string;
  top_n?: number;
  meta_filters?: MetaFilters;
};

export type Evidence = {
  view_type: string;
  snippet: string;
  rank: number;
};

export type SearchResult = {
  item_id: string;
  title: string;
  score: number;
  evidence: Evidence[];
  user_tags: string[];
  images: string[];
};

export type SearchResponse = {
  query_id: string;
  results: SearchResult[];
};

export type FeedbackRequest = {
  query_id: string;
  item_id: string;
  vote: 1 | -1;
  reason?: string;
};

export type FeedbackResponse = {
  ok: boolean;
  feedback_id: number;
};

export async function searchItems(payload: SearchRequest): Promise<SearchResponse> {
  const response = await fetch("/v1/search", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || "Search failed");
  }

  return response.json();
}

export async function sendFeedback(payload: FeedbackRequest): Promise<FeedbackResponse> {
  const response = await fetch("/v1/feedback", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || "Feedback failed");
  }

  return response.json();
}
