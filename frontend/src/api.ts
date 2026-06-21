// Typed client for the VideoDead API. Cookies carry the session.

export type Job = {
  id: string;
  url: string;
  mode: string;
  status: string;
  filename?: string | null;
  error?: string | null;
};

async function req<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const res = await fetch(`/api${path}`, {
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    ...opts,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const detail = body.detail;
    throw new Error(
      typeof detail === "string" ? detail : "Something went wrong. Please try again."
    );
  }
  return res.json() as Promise<T>;
}

export const api = {
  me: () => req<{ email: string }>("/me"),
  signup: (email: string, password: string) =>
    req("/signup", { method: "POST", body: JSON.stringify({ email, password }) }),
  login: (email: string, password: string, totp_code?: string) =>
    req("/login", { method: "POST", body: JSON.stringify({ email, password, totp_code }) }),
  logout: () => req("/logout", { method: "POST" }),
  submit: (url: string, mode: "video" | "audio") =>
    req<{ id: string }>("/jobs", { method: "POST", body: JSON.stringify({ url, mode }) }),
  jobs: () => req<Job[]>("/jobs"),
  fileUrl: (id: string) => `/api/files/${id}`,
  youtubeStatus: () => req<{ connected: boolean }>("/youtube/status"),
  disconnectYoutube: () => req<{ connected: boolean }>("/youtube/cookies", { method: "DELETE" }),
  uploadCookies: async (file: File): Promise<{ connected: boolean }> => {
    const fd = new FormData();
    fd.append("file", file);
    const res = await fetch("/api/youtube/cookies", {
      method: "POST", body: fd, credentials: "same-origin",
    });
    if (!res.ok) {
      const b = await res.json().catch(() => ({}));
      throw new Error(typeof b.detail === "string" ? b.detail : "Upload failed.");
    }
    return res.json() as Promise<{ connected: boolean }>;
  },
};
