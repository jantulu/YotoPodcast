import axios from "axios";

const baseURL = import.meta.env.VITE_API_BASE || "http://localhost:8000";
export const api = axios.create({ baseURL });

export async function getPodcasts() {
  const { data } = await api.get("/api/podcasts");
  return data;
}

export async function getEpisodes(podcastId: string) {
  const { data } = await api.get(`/api/podcasts/${podcastId}/episodes`);
  return data;
}

export async function uploadToYoto(podcastTitle: string, episodes: any[]) {
  const { data } = await api.post("/api/yoto/upload", { podcastTitle, episodes });
  return data;
}
