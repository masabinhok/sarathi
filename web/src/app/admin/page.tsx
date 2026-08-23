"use client";

import {
  useCallback,
  useEffect,
  useRef,
  useState,
  useSyncExternalStore,
} from "react";
import Header from "@/components/Header";
import { adminFetch } from "@/lib/api";

const TOKEN_KEY = "ioe.admin_token";
const TOKEN_EVENT = "ioe:admin-token";

type Doc = { name: string; bytes: number; chunks: number };
type Status = {
  documents: Doc[];
  total_chunks: number;
  text_model: string;
  embedding_model: string;
};

function kb(bytes: number) {
  return `${(bytes / 1024).toFixed(1)} KB`;
}

/**
 * localStorage is an external store, so it is read through useSyncExternalStore rather
 * than copied into state by an effect: that keeps the token correct across tabs and
 * avoids the cascading render that a setState-in-effect would cause.
 */
const tokenStore = {
  subscribe(onChange: () => void) {
    window.addEventListener("storage", onChange);
    window.addEventListener(TOKEN_EVENT, onChange);
    return () => {
      window.removeEventListener("storage", onChange);
      window.removeEventListener(TOKEN_EVENT, onChange);
    };
  },
  get: () => localStorage.getItem(TOKEN_KEY) ?? "",
  // Rendered on the server and on the first client pass, before localStorage is read.
  server: () => "",
};

function setStoredToken(value: string) {
  if (value) localStorage.setItem(TOKEN_KEY, value);
  else localStorage.removeItem(TOKEN_KEY);
  window.dispatchEvent(new Event(TOKEN_EVENT));
}

export default function Admin() {
  const token = useSyncExternalStore(
    tokenStore.subscribe,
    tokenStore.get,
    tokenStore.server,
  );
  const [entry, setEntry] = useState("");
  const [status, setStatus] = useState<Status | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);

  const load = useCallback(async (value: string) => {
    if (!value) return;
    try {
      setStatus(await adminFetch("/api/admin/status", value));
      setError(null);
    } catch (err) {
      setStatus(null);
      setError(err instanceof Error ? err.message : "could not load status");
    }
  }, []);

  // State is set from the promise callbacks, never synchronously in the effect body.
  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    adminFetch("/api/admin/status", token)
      .then((data) => {
        if (cancelled) return;
        setStatus(data);
        setError(null);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setStatus(null);
        setError(err instanceof Error ? err.message : "could not load status");
      });
    return () => {
      cancelled = true;
    };
  }, [token]);

  async function run(label: string, fn: () => Promise<string>) {
    setBusy(label);
    setNote(null);
    setError(null);
    try {
      setNote(await fn());
      await load(token);
    } catch (err) {
      setError(err instanceof Error ? err.message : `${label} failed`);
    } finally {
      setBusy(null);
    }
  }

  function signOut() {
    setStoredToken("");
    setStatus(null);
    setNote(null);
    setError(null);
  }

  if (!token) {
    return (
      <div className="flex min-h-dvh flex-col">
        <Header />
        <main className="mx-auto w-full max-w-md flex-1 px-5 py-16">
          <h1 className="font-display text-[1.5rem] font-medium tracking-[-0.01em]">
            Admin
          </h1>
          <p className="text-mute mt-2 text-sm leading-relaxed">
            Enter the admin token to manage documents and rebuild the index. It
            is the
            <code className="font-mono text-xs"> ADMIN_TOKEN </code>
            set in the server&apos;s{" "}
            <code className="font-mono text-xs">.env</code>.
          </p>
          <form
            className="mt-6 flex gap-2"
            onSubmit={(event) => {
              event.preventDefault();
              const value = entry.trim();
              if (!value) return;
              setStoredToken(value);
              setEntry("");
            }}
          >
            <input
              type="password"
              value={entry}
              onChange={(event) => setEntry(event.target.value)}
              placeholder="Admin token"
              aria-label="Admin token"
              className="border-rule focus:border-lapis flex-1 rounded-[7px] border bg-transparent px-3 py-2.5 text-sm outline-none"
            />
            <button
              type="submit"
              className="bg-lapis text-paper rounded-[7px] px-4 py-2.5 text-sm font-medium"
            >
              Continue
            </button>
          </form>
          {error && <p className="text-crimson mt-3 text-sm">{error}</p>}
        </main>
      </div>
    );
  }

  return (
    <div className="flex min-h-dvh flex-col">
      <Header />
      <main className="mx-auto w-full max-w-4xl flex-1 px-5 py-8">
        <div className="border-rule mb-6 flex items-baseline justify-between border-b pb-3">
          <h1 className="font-display text-[1.5rem] font-medium tracking-[-0.01em]">
            Admin
          </h1>
          <button
            onClick={signOut}
            className="text-faint hover:text-lapis text-xs underline underline-offset-2"
          >
            Forget token
          </button>
        </div>

        {error && (
          <p className="border-crimson/40 text-crimson bg-crimson-soft mb-4 rounded-[10px] border px-3.5 py-2.5 text-sm">
            {error}
          </p>
        )}
        {note && (
          <p className="border-rule-strong text-mute bg-card mb-4 rounded-[10px] border px-3.5 py-2.5 text-sm">
            {note}
          </p>
        )}

        <section className="mb-8">
          <p className="eyebrow mb-2">Add a document</p>
          <p className="text-mute mb-3 text-sm leading-relaxed">
            English Markdown with YAML frontmatter, as described in{" "}
            <code className="font-mono text-xs">docs/README.md</code>. Uploading
            replaces a file of the same name. The index is rebuilt separately,
            so nothing changes for students until you rebuild.
          </p>
          <div className="flex flex-wrap items-center gap-2">
            <input
              ref={fileInput}
              type="file"
              accept=".md"
              aria-label="Markdown file"
              className="text-mute file:border-rule file:text-ink hover:file:border-rule-strong max-w-full text-sm file:mr-3 file:rounded-[7px] file:border file:bg-transparent file:px-3 file:py-1.5 file:text-sm"
            />
            <button
              disabled={busy !== null}
              onClick={() =>
                run("upload", async () => {
                  const file = fileInput.current?.files?.[0];
                  if (!file) throw new Error("Choose a .md file first.");
                  const body = new FormData();
                  body.append("file", file);
                  const result = await adminFetch(
                    "/api/admin/documents",
                    token,
                    {
                      method: "POST",
                      body,
                    },
                  );
                  if (fileInput.current) fileInput.current.value = "";
                  return `${result.name} ${result.replaced ? "replaced" : "added"}. Rebuild the index to publish it.`;
                })
              }
              className="border-rule hover:border-rule-strong rounded-[7px] border px-3 py-1.5 text-sm transition disabled:opacity-40"
            >
              {busy === "upload" ? "Uploading…" : "Upload"}
            </button>
          </div>
        </section>

        <section className="mb-8">
          <div className="border-rule mb-3 flex flex-wrap items-baseline justify-between gap-2 border-b pb-2">
            <p className="eyebrow">
              Indexed documents
              {status ? ` · ${status.total_chunks} chunks` : ""}
            </p>
            <div className="flex gap-2">
              <button
                disabled={busy !== null}
                onClick={() =>
                  run("reindex", async () => {
                    const result = await adminFetch(
                      "/api/admin/reindex",
                      token,
                      {
                        method: "POST",
                      },
                    );
                    return `Index rebuilt — ${result.chunks} chunks.`;
                  })
                }
                className="bg-lapis text-paper rounded-[7px] px-3 py-1.5 text-xs font-medium transition disabled:opacity-40"
              >
                {busy === "reindex" ? "Rebuilding…" : "Rebuild index"}
              </button>
              <button
                disabled={busy !== null}
                onClick={() =>
                  run("notices", async () => {
                    const result = await adminFetch(
                      "/api/admin/notices/refresh",
                      token,
                      {
                        method: "POST",
                      },
                    );
                    const failed = Object.entries(
                      result.sources as Record<string, { error: string }>,
                    )
                      .filter(([, value]) => value.error)
                      .map(([key]) => key);
                    return failed.length
                      ? `${result.count} notices collected. Failed: ${failed.join(", ")}.`
                      : `${result.count} notices collected from all sources.`;
                  })
                }
                className="border-rule hover:border-rule-strong rounded-[7px] border px-3 py-1.5 text-xs transition disabled:opacity-40"
              >
                {busy === "notices" ? "Fetching…" : "Refresh notices"}
              </button>
            </div>
          </div>

          {status && (
            <ul className="divide-rule divide-y">
              {status.documents.map((doc) => (
                <li
                  key={doc.name}
                  className="flex items-center justify-between gap-4 py-2.5"
                >
                  <div className="min-w-0">
                    <p className="truncate font-mono text-[13px]">{doc.name}</p>
                    <p className="text-faint text-xs">
                      {kb(doc.bytes)} · {doc.chunks} chunk
                      {doc.chunks === 1 ? "" : "s"}
                      {doc.chunks === 0 && " · not in the index yet"}
                    </p>
                  </div>
                  <button
                    disabled={busy !== null}
                    onClick={() =>
                      run("delete", async () => {
                        await adminFetch(
                          `/api/admin/documents/${doc.name}`,
                          token,
                          {
                            method: "DELETE",
                          },
                        );
                        return `${doc.name} removed. Rebuild the index to apply it.`;
                      })
                    }
                    className="text-faint hover:text-crimson shrink-0 text-xs underline underline-offset-2 transition"
                  >
                    Remove
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>

        {status && (
          <p className="text-faint font-mono text-xs">
            {status.text_model} · {status.embedding_model}
          </p>
        )}
      </main>
    </div>
  );
}
