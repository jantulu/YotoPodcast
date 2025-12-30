import React, { useEffect, useState } from "react";
import { api } from "../api";
import type { Podcast, Episode } from "../types";
import UploadButton from "../components/UploadButton";

export default function PodcastsPage() {
  const [pods, setPods] = useState<Podcast[]>([]);
  const [slug, setSlug] = useState<string>("");
  const [episodes, setEpisodes] = useState<Episode[]>([]);
  const [err, setErr] = useState<string>("");

  useEffect(() => {
    (async () => {
      try {
        const p = await api.podcasts();
        setPods(p);
        if (p[0]) setSlug(p[0].slug);
      } catch (e) {
        setErr(String(e));
      }
    })();
  }, []);

  useEffect(() => {
    if (!slug) return;
    (async () => {
      setErr("");
      setEpisodes([]);
      try {
        const eps = await api.episodes(slug);
        setEpisodes(eps);
      } catch (e) {
        setErr(String(e));
      }
    })();
  }, [slug]);

  return (
    <>
      <div className="card">
        <h2>Podcasts</h2>
        <div className="row">
          <label className="small">Select:</label>
          <select value={slug} onChange={(e) => setSlug(e.target.value)}>
            {pods.map((p) => (
              <option key={p.slug} value={p.slug}>
                {p.title}
              </option>
            ))}
          </select>
        </div>
        {err && <div className="small" style={{ marginTop: 10 }}>Error: {err}</div>}
      </div>

      <div className="card">
        <h2>Episodes</h2>
        {episodes.length === 0 && !err && <div className="small">No episodes loaded.</div>}
        {episodes.map((ep) => (
          <div key={ep.id} className="card" style={{ margin: "12px 0" }}>
            <div className="row" style={{ justifyContent: "space-between" }}>
              <div>
                <div><strong>{ep.title}</strong></div>
                <div className="small" style={{ wordBreak: "break-all" }}>{ep.audioUrl}</div>
              </div>
              <UploadButton audioUrl={ep.audioUrl} title={ep.title} />
            </div>
          </div>
        ))}
      </div>
    </>
  );
}
