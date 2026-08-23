/**
 * Carrying a question from the landing page to /ask.
 *
 * It used to travel as `?q=`, which put the question in the address bar — so every
 * refresh asked it again, and every refresh opened another conversation in the history.
 * A URL should say which conversation you are reading, not re-send a message; that is
 * what `?c=` below is for. The question itself is handed over out of band and taken
 * straight back out, so it is asked exactly once.
 */

const HANDOFF_KEY = "ioe.pending_question";
const THREAD_PARAM = "c";

export function handOver(question: string): void {
  sessionStorage.setItem(HANDOFF_KEY, question);
}

/** Reads the handed-over question and consumes it. Returns "" when there is none. */
export function takeHandoff(): string {
  const question = sessionStorage.getItem(HANDOFF_KEY);
  if (question) sessionStorage.removeItem(HANDOFF_KEY);
  return question ?? "";
}

/** The conversation named by the current address, if it names one. */
export function threadFromUrl(): string | null {
  return new URLSearchParams(window.location.search).get(THREAD_PARAM);
}

/**
 * Point the address at a conversation. Replaces rather than pushes: opening a thread
 * is not a page you want the back button to walk through one by one, and Next's own
 * router would re-render the route for what is only a change of address.
 */
export function showThreadInUrl(threadId: string | null): void {
  const url = new URL(window.location.href);
  if (threadId) url.searchParams.set(THREAD_PARAM, threadId);
  else url.searchParams.delete(THREAD_PARAM);
  window.history.replaceState(null, "", url);
}
