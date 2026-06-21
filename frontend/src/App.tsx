import { useEffect, useState } from "react";
import { api, type Job } from "./api";

// One file, three simple screens: first-run setup, login, and the downloader.
export default function App() {
  const [screen, setScreen] = useState<"loading" | "setup" | "login" | "app">("loading");

  useEffect(() => {
    api
      .state()
      .then((s) => setScreen(s.needs_setup ? "setup" : "login"))
      .catch(() => setScreen("login"));
  }, []);

  return (
    <div className="min-h-screen flex items-center justify-center p-4 text-white">
      <div className="w-full max-w-xl">
        <h1 className="font-display text-4xl tracking-tight mb-1">
          VideoDead<span className="text-teal">.</span>
        </h1>
        <p className="text-white/70 mb-6 text-sm">Paste a link, get the file.</p>

        {screen === "loading" && <Card><p className="text-white/70">Loading…</p></Card>}
        {screen === "setup" && <Setup onDone={() => setScreen("login")} />}
        {screen === "login" && <Login onDone={() => setScreen("app")} />}
        {screen === "app" && <Downloader onSignOut={() => setScreen("login")} />}
      </div>
    </div>
  );
}

function Card({ children }: { children: React.ReactNode }) {
  return <div className="bg-white/5 border border-white/10 rounded-2xl p-6 backdrop-blur">{children}</div>;
}

function ErrorMsg({ msg }: { msg: string }) {
  return msg ? <p className="text-red-300 text-sm mt-3">{msg}</p> : null;
}

function Setup({ onDone }: { onDone: () => void }) {
  const [pw, setPw] = useState("");
  const [err, setErr] = useState("");
  async function go() {
    setErr("");
    try {
      await api.setup(pw);
      onDone();
    } catch (e) {
      setErr((e as Error).message);
    }
  }
  return (
    <Card>
      <h2 className="text-lg font-semibold mb-2">Create your password</h2>
      <p className="text-white/60 text-sm mb-4">
        First time setup. Choose a strong password (12+ characters, mixing letters, numbers and symbols).
      </p>
      <input
        type="password"
        value={pw}
        onChange={(e) => setPw(e.target.value)}
        placeholder="New password"
        className="w-full rounded-lg bg-white text-ink px-4 py-3 outline-none"
      />
      <button onClick={go} className="mt-4 w-full rounded-lg bg-teal text-ink font-semibold py-3">
        Create password
      </button>
      <ErrorMsg msg={err} />
    </Card>
  );
}

function Login({ onDone }: { onDone: () => void }) {
  const [pw, setPw] = useState("");
  const [code, setCode] = useState("");
  const [err, setErr] = useState("");
  async function go() {
    setErr("");
    try {
      await api.login(pw, code || undefined);
      onDone();
    } catch (e) {
      setErr((e as Error).message);
    }
  }
  return (
    <Card>
      <h2 className="text-lg font-semibold mb-4">Sign in</h2>
      <input
        type="password"
        value={pw}
        onChange={(e) => setPw(e.target.value)}
        placeholder="Password"
        className="w-full rounded-lg bg-white text-ink px-4 py-3 outline-none mb-3"
        onKeyDown={(e) => e.key === "Enter" && go()}
      />
      <input
        value={code}
        onChange={(e) => setCode(e.target.value)}
        placeholder="6-digit code (only if you enabled it)"
        className="w-full rounded-lg bg-white text-ink px-4 py-3 outline-none"
        onKeyDown={(e) => e.key === "Enter" && go()}
      />
      <button onClick={go} className="mt-4 w-full rounded-lg bg-teal text-ink font-semibold py-3">
        Sign in
      </button>
      <ErrorMsg msg={err} />
    </Card>
  );
}

function Downloader({ onSignOut }: { onSignOut: () => void }) {
  const [url, setUrl] = useState("");
  const [mode, setMode] = useState<"video" | "audio">("video");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState("");
  const [jobs, setJobs] = useState<Job[]>([]);

  async function refresh() {
    try {
      setJobs(await api.jobs());
    } catch { /* ignore */ }
  }
  useEffect(() => { refresh(); }, []);

  async function download() {
    setErr(""); setStatus(""); setProgress(0);
    if (!url.trim()) { setErr("Please paste a video link first."); return; }
    setBusy(true);
    try {
      const { id } = await api.submit(url.trim(), mode);
      const ws = new WebSocket(
        `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/api/ws/${id}`
      );
      ws.onmessage = (ev) => {
        const p = JSON.parse(ev.data);
        setProgress(p.progress || 0);
        setStatus(
          p.status === "done" ? "Done!" :
          p.status === "error" ? "" : "Downloading…"
        );
        if (p.status === "error") setErr(p.error || "That link could not be downloaded.");
        if (p.status === "done" || p.status === "error") {
          ws.close(); setBusy(false); setUrl(""); refresh();
        }
      };
      ws.onerror = () => { setBusy(false); setErr("Connection lost. Please try again."); };
    } catch (e) {
      setBusy(false);
      setErr((e as Error).message);
    }
  }

  return (
    <Card>
      <input
        value={url}
        onChange={(e) => setUrl(e.target.value)}
        placeholder="Paste a video link here"
        className="w-full rounded-lg bg-white text-ink px-4 py-4 text-lg outline-none"
      />
      <div className="flex gap-2 mt-3">
        {(["video", "audio"] as const).map((m) => (
          <button
            key={m}
            onClick={() => setMode(m)}
            className={`flex-1 rounded-lg py-2 font-medium border ${
              mode === m ? "bg-teal text-ink border-teal" : "bg-transparent text-white/80 border-white/20"
            }`}
          >
            {m === "video" ? "Video" : "Audio only"}
          </button>
        ))}
      </div>

      <button
        onClick={download}
        disabled={busy}
        className="mt-4 w-full rounded-lg bg-teal text-ink font-semibold py-4 text-lg disabled:opacity-60"
      >
        {busy ? "Working…" : "⬇  Download"}
      </button>

      {(busy || progress > 0) && (
        <div className="mt-4">
          <div className="h-3 w-full bg-white/10 rounded-full overflow-hidden">
            <div className="h-full bg-teal transition-all" style={{ width: `${progress}%` }} />
          </div>
          <p className="text-white/70 text-sm mt-2">{Math.round(progress)}% · {status}</p>
        </div>
      )}
      <ErrorMsg msg={err} />

      {jobs.length > 0 && (
        <div className="mt-6">
          <p className="text-white/50 text-xs uppercase tracking-widest mb-2">Finished</p>
          <ul className="divide-y divide-white/10">
            {jobs.filter((j) => j.status === "done").map((j) => (
              <li key={j.id} className="py-2 flex items-center justify-between">
                <span className="text-sm truncate mr-3">{j.filename || j.url}</span>
                <a href={api.fileUrl(j.id)} className="text-teal text-sm shrink-0">Download ⬇</a>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="mt-6 flex justify-between text-xs text-white/40">
        <span>For content you have the right to download.</span>
        <button onClick={() => api.logout().then(onSignOut)} className="hover:text-white/70">Sign out</button>
      </div>
    </Card>
  );
}
