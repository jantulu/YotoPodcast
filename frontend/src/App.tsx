import React, { useEffect, useState } from "react";
import { api } from "./api";
import AuthPage from "./pages/AuthPage";
import PodcastsPage from "./pages/PodcastsPage";
import type { AuthStatus } from "./types";

export default function App() {
  const [auth, setAuth] = useState<AuthStatus>({ authenticated: false });
  const [loading, setLoading] = useState(true);

  async function refreshAuth() {
    try {
      const s = await api.authStatus();
      setAuth(s);
    } catch (e) {
      setAuth({ authenticated: false, error: String(e) });
    }
  }

  useEffect(() => {
    (async () => {
      setLoading(true);
      await refreshAuth();
      setLoading(false);
    })();
  }, []);

  if (loading) {
    return (
      <div className="container">
        <div className="card">Loading…</div>
      </div>
    );
  }

  return (
    <div className="container">
      <h1>Podcast → Yoto</h1>
      <div className="row" style={{ marginBottom: 12 }}>
        {"authenticated" in auth && auth.authenticated ? (
          <span className="badge">Authenticated</span>
        ) : (
          <span className="badge">Not authenticated</span>
        )}
        <button onClick={refreshAuth}>Refresh auth</button>
      </div>

      {("authenticated" in auth && auth.authenticated) ? (
        <PodcastsPage />
      ) : (
        <AuthPage auth={auth} onAuthed={refreshAuth} />
      )}
    </div>
  );
}
