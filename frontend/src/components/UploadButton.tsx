import React, { useState } from "react";
import { api } from "../api";

export default function UploadButton({ audioUrl, title }: { audioUrl: string; title: string }) {
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<string>("");

  async function run() {
    setBusy(true);
    setResult("");
    try {
      const r = await api.upload(audioUrl, title);
      const sha = (r.transcoded && (r.transcoded.sha || r.transcoded.SHA)) ?? undefined;
      setResult(`Uploaded. uploadId=${r.uploadId}${sha ? ` sha=${sha}` : ""}`);
    } catch (e) {
      setResult(String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="row">
      <button onClick={() => run()} disabled={busy}>
        {busy ? "Uploading…" : "Upload to Yoto"}
      </button>
      {result && <span className="small">{result}</span>}
    </div>
  );
}
