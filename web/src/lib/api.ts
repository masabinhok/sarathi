export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type Role = "user" | "assistant";

export type Message = {
  role: Role;
  content: string;
};

type StreamHandlers = {
  onToken: (text: string) => void;
  onThread?: (threadId: string) => void;
  onError?: (message: string) => void;
};

/** Reads an SSE body and dispatches `event:`/`data:` pairs as they arrive. */
async function readSSE(
  response: Response,
  onEvent: (event: string, data: Record<string, string>) => void,
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
    if (event === "token") handlers.onToken(data.text);
    else if (event === "start") handlers.onThread?.(data.thread_id);
    else if (event === "error") handlers.onError?.(data.message);
  });
}

export async function fetchHistory(threadId: string): Promise<Message[]> {
  const response = await fetch(`${API_URL}/api/history/${threadId}`);
  if (!response.ok) return [];
  return response.json();
}
