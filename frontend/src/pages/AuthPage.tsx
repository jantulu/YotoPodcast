import React, { useEffect, useRef, useState } from "react";
import { api } from "../api";
import type { AuthStatus } from "../types";

function extractCodeFromUrl(url?: string): string | undefined {
  if (!url) return undefined;
  try {
    const u = new URL(url);
    // common: ?user_code=XXXX or ?code=...
    return u.searchParams.get("user_code") ?? u.searchParams.get("code") ?? undefined;
  } catch {
    return undefined;
  }
}

export default function AuthPage({ auth, onAuthed }: { auth: AuthStatus; onAuthed: () => void }) {
  const [msg, setMsg] = useState<string>("");
  const [polling, setPolling] = useState(false);
  const timer = useRef<number | null>(null);

  async function start() {
    setMsg("");
    const startResp = await api.authStart();
    const url = startResp.verification_uri_complete || startResp.verification_uri;
    const code = startResp.user_code || extractCodeFromUrl(startResp.verification_uri_complete);

    if (url) {
      window.open(url, "_blank", "noopener,noreferrer");
    }
    setMsg(
      url
        ? `Opened Yoto login page. ${code ? `Code: ${code}` : "If no code is visible, it may be embedded in the URL."}`
        : "Started auth, but no verification URL was returned."
    );

    setPolling(true);
  }

  async function tick() {
    const s = await api.authStatus();
    if ("authenticated" in s && s.authenticated) {
      setPolling(false);
      setMsg("Authenticated!");
      onAuthed();
      return;
    }
  }

  useEffect(() => {
    if (!polling) {
      if (timer.current) window.clearInterval(timer.current);
      timer.current = null;
      return;
    }
    // poll every 5s (safe default; backend may indicate slow_down via status payload)
    timer.current = window.setInterval(() => {
      tick().catch((e) => setMsg(String(e)));
    }, 5000);

    return () => {
      if (timer.current) window.clearInterval(timer.current);
      timer.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [polling]);

  const pendingCode =
    ("pending" in auth && auth.pending && (auth.user_code || extractCodeFromUrl(auth.verification_uri_complete))) || undefined;

  return (
    <div className="card">
      <h2>Authenticate with Yoto</h2>
      <p className="small">
        This app uses Yoto OAuth Device Flow. One shared token is stored in <code>/data/yoto_token.json</code>.
      </p>

      <div className="row">
        <button onClick={() => start().catch((e) => setMsg(String(e)))}>Authenticate with Yoto</button>
        <button onClick={() => setPolling((p) => !p)} disabled={("authenticated" in auth && auth.authenticated)}>
          {polling ? "Stop polling" : "Start polling"}
        </button>
      </div>

      {"pending" in auth && auth.pending && (
        <div style={{ marginTop: 12 }}>
          <div className="small">Auth pending…</div>
          {auth.verification_uri_complete && (
            <div className="small">
              Link:{" "}
              <a href={auth.verification_uri_complete} target="_blank" rel="noreferrer">
                open verification page
              </a>
            </div>
          )}
          {pendingCode && <div className="small">Code: {pendingCode}</div>}
        </div>
      )}

      {("authenticated" in auth && !auth.authenticated && auth.error) && (
        <div style={{ marginTop: 12 }} className="small">
          Error: {auth.error}
        </div>
      )}

      {msg && (
        <div style={{ marginTop: 12 }} className="small">
          {msg}
        </div>
      )}
    </div>
  );
}
