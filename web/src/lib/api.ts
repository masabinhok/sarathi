export const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type Role = "user" | "assistant";

/** A document an answer was drawn from, as retrieval recorded it. */
export type Source = {
  title: string;
  year: string | null;
  url: string | null;
  file: string;
  sections: string[];
};

export type Message = {
  role: Role;
  content: string;
  sources?: Source[];
};

type StreamHandlers = {
  onToken: (text: string) => void;
  onThread?: (threadId: string) => void;
  onSources?: (sources: Source[]) => void;
  onError?: (message: string) => void;
};

/** Reads an SSE body and dispatches `event:`/`data:` pairs as they arrive. */
async function readSSE(
  response: Response,
  onEvent: (event: string, data: Record<string, unknown>) => void,
) {
  const reader = response.body?.getReader();
  if (!reader) throw new Error("response has no body");

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const frames = buffer.split("\n\n");
    buffer = frames.pop() ?? "";

    for (const frame of frames) {
      let event = "message";
      let data = "";
      for (const line of frame.split("\n")) {
        if (line.startsWith("event:")) event = line.slice(6).trim();
        else if (line.startsWith("data:")) data += line.slice(5).trim();
      }
      if (data) onEvent(event, JSON.parse(data));
    }
  }
}

export async function sendMessage(
  message: string,
  threadId: string | null,
  handlers: StreamHandlers,
  signal?: AbortSignal,
) {
  const response = await fetch(`${API_URL}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, thread_id: threadId }),
    signal,
  });

  if (!response.ok) throw new Error(`backend returned ${response.status}`);

  await readSSE(response, (event, data) => {
    if (event === "token") handlers.onToken(data.text as string);
    else if (event === "start") handlers.onThread?.(data.thread_id as string);
    else if (event === "sources")
      handlers.onSources?.(data.sources as Source[]);
    else if (event === "error") handlers.onError?.(data.message as string);
  });
}

export async function fetchHistory(threadId: string): Promise<Message[]> {
  const response = await fetch(`${API_URL}/api/history/${threadId}`);
  if (!response.ok) return [];
  return response.json();
}

export type Health = {
  status: string;
  model: string;
  embedding_model: string;
  documents: number;
  chunks: number;
};

export type Today = {
  ad_date: string;
  ad_label: string;
  weekday: string;
  bs_date: string;
  bs_label: string;
};

export type Notice = {
  title: string;
  url: string;
  date: string;
  source: string;
  source_label: string;
  bs_date: string;
  bs_label: string;
};

export type NoticeFeed = {
  updated_at: string;
  sources: Record<
    string,
    { label: string; url: string; count: number; error: string }
  >;
  notices: Notice[];
};

export type Deadline = {
  bs_date: string;
  bs_label: string;
  ad_date: string;
  days: number;
  status: "upcoming" | "today" | "passed";
  snippet: string;
  document: string;
  url: string;
  file: string;
};

export type DeadlineFeed = {
  today_nepal: string;
  upcoming: Deadline[];
  passed: Deadline[];
};

async function getJSON<T>(path: string): Promise<T> {
  const response = await fetch(`${API_URL}${path}`);
  if (!response.ok) throw new Error(`${path} returned ${response.status}`);
  return response.json();
}

export const fetchHealth = () => getJSON<Health>("/api/health");
export const fetchToday = () => getJSON<Today>("/api/today");
export const fetchNotices = () => getJSON<NoticeFeed>("/api/notices");
export const fetchDeadlines = () => getJSON<DeadlineFeed>("/api/deadlines");

/** Admin calls carry the shared token; the caller holds it, it is never persisted here. */
export async function adminFetch(
  path: string,
  token: string,
  init: RequestInit = {},
) {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { ...(init.headers ?? {}), "X-Admin-Token": token },
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(body?.detail ?? `request failed (${response.status})`);
  }
  return body;
}
