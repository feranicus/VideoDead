// Thin typed client for the VideoDead API. Cookies carry the session.

export type AppState = { needs_setup: boolean };
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
    throw new Error(body.detail || "Something went wrong. Please try again.");
  }
  return res.json() as Promise<T>;
}

export const api = {
  state: () => req<AppState>("/state"),
  setup: (password: string) =>
    req("/setup", { method: "POST", body: JSON.stringify({ password }) }),
  login: (password: string, totp_code?: string) =>
    req("/login", { method: "POST", body: JSON.stringify({ password, totp_code }) }),
  logout: () => req("/logout", { method: "POST" }),
  submit: (url: string, mode: "video" | "audio") =>
    req<{ id: string }>("/jobs", { method: "POST", body: JSON.stringify({ url, mode }) }),
  jobs: () => req<Job[]>("/jobs"),
  fileUrl: (id: string) => `/api/files/${id}`,
};
