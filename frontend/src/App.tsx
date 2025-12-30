import { useEffect, useMemo, useState } from "react";

const API_BASE =
  (import.meta.env?.VITE_API_BASE?.replace(/\/+$/, "") as string) ||
  `${window.location.protocol}//${window.location.hostname}:8001`;

type AuthStatus = {
  authenticated: boolean;
  expires_at?: number; // unix seconds
  error?: string;
};

async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const r = await fetch(url, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
    cache: "no-store",
  });
  const text = await r.text();
  let data: any = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = text;
  }
  if (!r.ok) {
    throw new Error(typeof data === "string" ? data : JSON.stringify(data));
  }
  return data as T;
}

function formatExpires(expires_at?: number) {
  if (!expires_at) return "";
  const d = new Date(expires_at * 1000);
  return d.toLocaleString();
}

export default function App() {
  const [auth, setAuth] = useState<AuthStatus>({ authenticated: false });
  const [authLoading, setAuthLoading] = useState<boolean>(true);
  const [authError, setAuthError] = useState<string>("");

  const isAuthed = !!auth?.authenticated;

  // On load: check status
  useEffect(() => {
    let cancelled = false;

    async function checkOnce() {
      setAuthLoading(true);
      setAuthError("");
      try {
        const s = await fetchJson<AuthStatus>(`${API_BASE}/api/yoto/auth/status`);
        if (!cancelled) setAuth(s);
      } catch (e: any) {
        if (!cancelled) setAuthError(e?.message || String(e));
      } finally {
        if (!cancelled) setAuthLoading(false);
      }
    }

    checkOnce();
    return () => {
      cancelled = true;
    };
  }, []);

  // Poll while not authenticated
  useEffect(() => {
    if (isAuthed) return;

    let cancelled = false;
    const timer = setInterval(async () => {
      try {
        const s = await fetchJson<AuthStatus>(`${API_BASE}/api/yoto/auth/status`);
        if (!cancelled) setAuth(s);
      } catch (e: any) {
        // Keep polling; just show latest error.
        if (!cancelled) setAuthError(e?.message || String(e));
      }
    }, 2000);

    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [isAuthed]);

  async function startAuth() {
    setAuthError("");
    try {
      // your backend should return something like:
      // { verification_uri_complete, user_code, device_code, interval }
      const info = await fetchJson<any>(`${API_BASE}/api/yoto/auth/start`, {
        method: "POST",
        body: JSON.stringify({}),
      });

      // If backend returns a URL for the user to complete, open it
      const url =
        info?.verification_uri_complete || info?.verification_uri || info?.url;
      if (url) window.open(url, "_blank", "noopener,noreferrer");

      // Immediately check status after starting
      const s = await fetchJson<AuthStatus>(`${API_BASE}/api/yoto/auth/status`);
      setAuth(s);
    } catch (e: any) {
      setAuthError(e?.message || String(e));
    }
  }

  return (
    <div style={{ fontFamily: "system-ui, sans-serif", padding: 16, maxWidth: 1100, margin: "0 auto" }}>
      <h2>Podcast → Yoto</h2>

      <div style={{ border: "1px solid #ddd", borderRadius: 8, padding: 12, marginBottom: 16 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12, justifyContent: "space-between" }}>
          <div>
            <div style={{ fontWeight: 700 }}>
              Yoto Authentication:{" "}
              {authLoading ? "checking…" : isAuthed ? "✅ authenticated" : "❌ not authenticated"}
            </div>
            {auth?.expires_at ? (
              <div style={{ fontSize: 13, opacity: 0.8 }}>
                Token expires: {formatExpires(auth.expires_at)}
              </div>
            ) : null}
            {authError ? (
              <div style={{ marginTop: 8, color: "#b00020", fontSize: 13 }}>
                {authError}
              </div>
            ) : null}
          </div>

          {!isAuthed ? (
            <button onClick={startAuth} style={{ padding: "8px 12px" }}>
              Connect Yoto
            </button>
          ) : (
            <button
              onClick={async () => {
                // manual re-check
                try {
                  const s = await fetchJson<AuthStatus>(`${API_BASE}/api/yoto/auth/status`);
                  setAuth(s);
                } catch (e: any) {
                  setAuthError(e?.message || String(e));
                }
              }}
              style={{ padding: "8px 12px" }}
            >
              Refresh Status
            </button>
          )}
        </div>

        <div style={{ marginTop: 10, fontSize: 12, opacity: 0.7 }}>
          API base: <code>{API_BASE}</code>
        </div>
      </div>

      {/* The rest of your app UI goes here.
          Gate Yoto actions behind isAuthed. */}
      <div style={{ border: "1px solid #ddd", borderRadius: 8, padding: 12 }}>
        <div style={{ fontWeight: 700, marginBottom: 6 }}>Next steps</div>
        {isAuthed ? (
          <div>Now you can enable upload/playlist UI here.</div>
        ) : (
          <div>Authenticate first to enable upload/playlist actions.</div>
        )}
      </div>
    </div>
  );
}
