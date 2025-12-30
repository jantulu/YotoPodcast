import type { AuthStart, AuthStatus, Podcast, Episode, UploadResult } from "./types";

const API_BASE =
  (import.meta as any).env?.VITE_API_BASE ??
  `${window.location.protocol}//${window.location.hostname}:8001`;

async function j<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, init);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${text}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => j<{ ok: boolean }>("/api/health"),

  authStart: () => j<AuthStart>("/api/yoto/auth/start", { method: "POST" }),
  authStatus: () => j<AuthStatus>("/api/yoto/auth/status"),

  podcasts: () => j<Podcast[]>("/api/podcasts"),
  episodes: (slug: string) => j<Episode[]>(`/api/podcasts/${encodeURIComponent(slug)}/episodes`),

  upload: (audioUrl: string, title: string) =>
    j<UploadResult>("/api/yoto/upload", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ audioUrl, title })
    })
};

export { API_BASE };
