import { useEffect, useRef, useState } from "react";
import { api, type Job } from "./api";

export default function App() {
  const [screen, setScreen] = useState<"loading" | "auth" | "app">("loading");
  const [email, setEmail] = useState("");

  useEffect(() => {
    api.me()
      .then((u) => { setEmail(u.email); setScreen("app"); })
      .catch(() => setScreen("auth"));
  }, []);

  return (
    <>
      <Chrome />
      <header className="topbar">
        <div className="brand"><span className="reel" />VIDEODEAD<span className="dot">.</span></div>
        {screen === "app" && (
          <div className="who">
            <span className="hidem">Signed in as <b>{email}</b></span>
            <button className="ghostbtn" onClick={() => api.logout().then(() => { setEmail(""); setScreen("auth"); })}>
              Sign out
            </button>
          </div>
        )}
      </header>

      <main className="shell">
        <Hero />
        {screen === "loading" && <div className="card reveal"><p className="hint">Loading the projector…</p></div>}
        {screen === "auth" && <Auth onAuthed={(em) => { setEmail(em); setScreen("app"); }} />}
        {screen === "app" && <Stage />}
      </main>
    </>
  );
}

/* ---------------- ambient cinema chrome ---------------- */
function Chrome() {
  const dust = useRef<HTMLCanvasElement>(null);
  const cur = useRef<HTMLDivElement>(null);
  const dot = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // custom cursor
    const c = cur.current, d = dot.current;
    const move = (e: MouseEvent) => {
      if (c) { c.style.left = `${e.clientX}px`; c.style.top = `${e.clientY}px`; }
      if (d) { d.style.left = `${e.clientX}px`; d.style.top = `${e.clientY}px`; }
    };
    const over = (e: MouseEvent) => {
      const hot = !!(e.target as HTMLElement)?.closest?.("button,a,input");
      c?.classList.toggle("hot", hot);
    };
    window.addEventListener("mousemove", move);
    window.addEventListener("mouseover", over);

    // floating projector dust
    const canvas = dust.current;
    const ctx = canvas?.getContext("2d") ?? null;
    let raf = 0;
    type P = { x: number; y: number; r: number; vx: number; vy: number; a: number };
    let parts: P[] = [];
    const resize = () => {
      if (!canvas) return;
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
      const n = Math.min(90, Math.floor(window.innerWidth / 16));
      parts = Array.from({ length: n }, () => ({
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        r: Math.random() * 1.6 + 0.3,
        vx: (Math.random() - 0.5) * 0.25,
        vy: (Math.random() - 0.5) * 0.25,
        a: Math.random() * 0.5 + 0.1,
      }));
    };
    resize();
    window.addEventListener("resize", resize);
    const tick = () => {
      if (ctx && canvas) {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        for (const p of parts) {
          p.x += p.vx; p.y += p.vy;
          if (p.x < 0) p.x = canvas.width; if (p.x > canvas.width) p.x = 0;
          if (p.y < 0) p.y = canvas.height; if (p.y > canvas.height) p.y = 0;
          ctx.beginPath();
          ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
          ctx.fillStyle = `rgba(233,205,150,${p.a})`;
          ctx.fill();
        }
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);

    return () => {
      window.removeEventListener("mousemove", move);
      window.removeEventListener("mouseover", over);
      window.removeEventListener("resize", resize);
      cancelAnimationFrame(raf);
    };
  }, []);

  return (
    <>
      <div className="bg"><div className="beam" /></div>
      <canvas id="dust" ref={dust} />
      <div className="grain" />
      <div className="vig" />
      <div className="bars top" />
      <div className="bars bot" />
      <div className="cur" ref={cur} />
      <div className="cur-dot" ref={dot} />
    </>
  );
}

function Hero() {
  return (
    <div className="hero reveal">
      <div className="eyebrow">Capture the reel</div>
      <h1 className="title">VIDEODEAD<span className="dot">.</span></h1>
      <div className="tagline">Any link in — <b>a clean file</b> out</div>
    </div>
  );
}

function Sprockets() {
  const dots = Array.from({ length: 9 });
  return (
    <>
      <div className="sprockets l">{dots.map((_, i) => <i key={`l${i}`} />)}</div>
      <div className="sprockets r">{dots.map((_, i) => <i key={`r${i}`} />)}</div>
    </>
  );
}

/* ---------------- auth ---------------- */
function Auth({ onAuthed }: { onAuthed: (email: string) => void }) {
  const [tab, setTab] = useState<"in" | "up">("in");
  const [email, setEmail] = useState("");
  const [pw, setPw] = useState("");
  const [code, setCode] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  async function go() {
    setErr(""); setBusy(true);
    try {
      if (tab === "up") await api.signup(email, pw);
      else await api.login(email, pw, code || undefined);
      const me = await api.me();
      onAuthed(me.email);
    } catch (e) {
      setErr((e as Error).message);
      setBusy(false);
    }
  }

  return (
    <div className="card reveal">
      <Sprockets />
      <div className="tabs">
        <button className={tab === "in" ? "on" : ""} onClick={() => setTab("in")}>Sign in</button>
        <button className={tab === "up" ? "on" : ""} onClick={() => setTab("up")}>Create account</button>
      </div>

      <div className="field">
        <label>Email</label>
        <input className="input" type="email" value={email} autoComplete="email"
          onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" />
      </div>
      <div className="field">
        <label>Password</label>
        <input className="input" type="password" value={pw}
          autoComplete={tab === "up" ? "new-password" : "current-password"}
          onChange={(e) => setPw(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && go()}
          placeholder={tab === "up" ? "At least 10 characters" : "Your password"} />
      </div>
      {tab === "in" && (
        <div className="field">
          <label>2-step code <span style={{ textTransform: "none", letterSpacing: 0 }}>(only if enabled)</span></label>
          <input className="input" value={code} inputMode="numeric"
            onChange={(e) => setCode(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && go()}
            placeholder="123 456" />
        </div>
      )}

      <button className="cta" onClick={go} disabled={busy}>
        {busy ? "Please wait…" : tab === "up" ? "Create account" : "Sign in"}
      </button>
      {err && <p className="err">{err}</p>}
      <p className="hint">For content you own or have the right to download.</p>
    </div>
  );
}

/* ---------------- downloader ---------------- */
function Stage() {
  const [url, setUrl] = useState("");
  const [mode, setMode] = useState<"video" | "audio">("video");
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState("");
  const [err, setErr] = useState("");
  const [jobs, setJobs] = useState<Job[]>([]);
  const [yt, setYt] = useState<boolean | null>(null);
  const [ytHelp, setYtHelp] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  async function refresh() {
    try { setJobs(await api.jobs()); } catch { /* ignore */ }
  }
  async function loadYt() {
    try { setYt((await api.youtubeStatus()).connected); } catch { setYt(false); }
  }
  useEffect(() => { refresh(); loadYt(); }, []);

  function onFile(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    if (!f) return;
    setErr("");
    api.uploadCookies(f).then(() => setYt(true)).catch((x: Error) => setErr(x.message));
    e.target.value = "";
  }

  function start() {
    setErr(""); setStatus(""); setProgress(0);
    if (!url.trim()) { setErr("Paste a video link first."); return; }
    setBusy(true);
    api.submit(url.trim(), mode)
      .then(({ id }) => {
        const proto = location.protocol === "https:" ? "wss" : "ws";
        const ws = new WebSocket(`${proto}://${location.host}/api/ws/${id}`);
        ws.onmessage = (ev) => {
          const p = JSON.parse(ev.data) as { progress?: number; status?: string; error?: string };
          setProgress(p.progress || 0);
          setStatus(p.status === "done" ? "Done" : p.status === "error" ? "" : "Downloading");
          if (p.status === "error") setErr(p.error || "That link could not be downloaded.");
          if (p.status === "done" || p.status === "error") {
            ws.close(); setBusy(false); setUrl(""); refresh();
          }
        };
        ws.onerror = () => { setBusy(false); setErr("Connection lost. Please try again."); };
      })
      .catch((e: Error) => { setBusy(false); setErr(e.message); });
  }

  const done = jobs.filter((j) => j.status === "done");

  return (
    <div className="card stage reveal">
      <Sprockets />
      <div className="marquee">
        <input className="input" value={url} onChange={(e) => setUrl(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !busy && start()}
          placeholder="Paste a video link here" />
      </div>

      <div className="toggle">
        {(["video", "audio"] as const).map((m) => (
          <button key={m} className={mode === m ? "on" : ""} onClick={() => setMode(m)}>
            {m === "video" ? "🎬 Video" : "🎧 Audio only"}
          </button>
        ))}
      </div>

      <div className="ytbar">
        <span className="ytlabel">
          <span className={`ytdot ${yt ? "on" : ""}`} />
          {yt ? "YouTube connected" : "YouTube not connected"}
        </span>
        <div className="ytactions">
          <button className="ytlink" onClick={() => setYtHelp((v) => !v)}>How?</button>
          {yt ? (
            <button className="ytbtn" onClick={() => api.disconnectYoutube().then(() => setYt(false))}>Disconnect</button>
          ) : (
            <button className="ytbtn" onClick={() => fileRef.current?.click()}>Connect YouTube</button>
          )}
        </div>
        <input ref={fileRef} type="file" accept=".txt" hidden onChange={onFile} />
      </div>
      {ytHelp && (
        <div className="ythelp">
          To download YouTube, connect <b>your own</b> account once: in your browser install the
          extension <b>“Get cookies.txt LOCALLY”</b>, open <b>youtube.com</b> while signed in,
          export <b>Netscape</b> format, then click <b>Connect YouTube</b> and pick that file.
          It’s stored privately for your account only.
        </div>
      )}

      <button className="action" onClick={start} disabled={busy}>
        {busy ? "Rolling…" : "⬇ Download"}
      </button>

      {(busy || progress > 0) && (
        <div className="scrub">
          <div className="bar"><div className="fill" style={{ width: `${progress}%` }} /></div>
          <div className="meta">
            <span>{busy && <span className="spinreel" />}{status || "Queued"}</span>
            <b>{Math.round(progress)}%</b>
          </div>
        </div>
      )}
      {err && <p className="err">{err}</p>}

      {done.length > 0 && (
        <div className="finished">
          <h4>Your reel</h4>
          {done.map((j) => (
            <div className="frow" key={j.id}>
              <div className="poster"><span>{j.mode === "audio" ? "🎧" : "🎞️"}</span></div>
              <div className="fname">{j.filename || j.url}</div>
              <a className="dl" href={api.fileUrl(j.id)}>Save ⬇</a>
            </div>
          ))}
        </div>
      )}

      <div className="foot">
        <span>Encrypted · auto-deletes after a while</span>
        <span>VIDEODEAD</span>
      </div>
    </div>
  );
}
