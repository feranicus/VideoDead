# VideoDead

A dead-simple, secure, **multi-user** web app to download streaming video and audio from any **lawful** source. One screen: paste a link, choose **Video** or **Audio only**, click **Download** — and your file is gone from the server the moment you save it.

Built on the [yt-dlp](https://github.com/yt-dlp/yt-dlp) engine, hosted on a single DigitalOcean droplet with Docker Compose. Live at **godeyes.ai**.

> The full visual design doc (with an animated, bilingual diagram of how it works) is [`docs/HLD.html`](docs/HLD.html). The YouTube setup guide is [`docs/YOUTUBE_COOKIES.md`](docs/YOUTUBE_COOKIES.md).

---

## What it does

- **Per-user accounts.** Anyone signs up with email + password. Each person's downloads, history, and YouTube connection are private to their account.
- **Downloads 1000+ sites** via yt-dlp — direct files, archive.org, Vimeo, and (with a per-user connection) YouTube.
- **Per-user YouTube.** Each user connects *their own* YouTube account — nobody shares one identity.
- **Self-cleaning storage.** A file is deleted from the server the instant the user finishes downloading it, with a 6-hour auto-purge as a backstop.
- **Cinematic UI.** A single, polished, mobile-friendly screen.
- **Secure by design** — HTTPS, login, per-user isolation, SSRF protection, hardened containers.

---

## Architecture

```
Internet --HTTPS--> Caddy (edge: auto-TLS, security headers)
                      |-- serves the React SPA (static)
                      `-- /api --> FastAPI --enqueue--> Redis --> Worker (arq + yt-dlp + Node + Deno)
                                      |                                    |
                                      `-- SQLite (users, jobs)             `-- /downloads (auto-cleaned)
```

| Container | Role |
|-----------|------|
| **caddy** | Public edge. Automatic HTTPS, security headers, serves the SPA, proxies `/api`. |
| **api** | FastAPI. Auth, input/SSRF validation, enqueues jobs, serves & deletes files. |
| **worker** | arq + yt-dlp. Does the downloading. Has `ffmpeg`, `Node`, and `Deno` (for YouTube). |
| **redis** | Job queue + live progress. Isolated network, no internet. |

State lives in two places: **SQLite** (`/data/videodead.sqlite`) holds users + job history; **Redis** holds the live queue and progress.

---

## Tech stack

| Layer | Choice | Why |
|-------|--------|-----|
| Frontend | React + Vite + TypeScript | Fast, type-safe single-page app |
| API | Python 3.12 + FastAPI | yt-dlp is Python -> call it as a library, no shelling out |
| Worker | arq + Redis | Long downloads run off the web request |
| Engine | yt-dlp **pinned** + ffmpeg + Node + Deno | Node/Deno solve YouTube's JS "n-challenge" |
| State | Redis + SQLite | Queue/progress in Redis, users/jobs in one SQLite file |
| Edge | Caddy | Automatic HTTPS + security headers, one-line config |
| Runtime | Docker Compose / Ubuntu | One droplet, one-command deploy |

---

## How it works, step by step

1. **Sign in.** The user creates an account (email + password, Argon2id-hashed) or logs in. A secure session cookie keeps them in.
2. **Paste a link.** The React UI sends it to the API.
3. **Safety check.** The API validates the URL: only `http/https`, and it blocks any address that resolves to a private/loopback/link-local/cloud-metadata IP (SSRF defence). It never downloads anything itself — it pushes a job onto Redis and returns immediately.
4. **The worker runs yt-dlp.** It picks up the job, downloads with safe fixed options, and reports progress to Redis. For YouTube it uses that user's cookies + Node/Deno to solve the challenge.
5. **Live progress.** The UI streams progress over a WebSocket until "Done".
6. **Save & forget.** The user clicks **Save**; the browser downloads the file. The moment the transfer finishes, the API **deletes the file from the server** and marks the job removed.

---

## Deploy on a DigitalOcean droplet

### First time
1. Ubuntu droplet with Docker. Point a domain's A record at the droplet IP.
2. Clone and run the deploy script:
   ```bash
   git clone https://github.com/feranicus/VideoDead.git /opt/videodead
   cd /opt/videodead
   sudo bash deploy.sh          # asks for DOMAIN + email, builds everything, gets HTTPS
   ```
3. Open `https://yourdomain` -> **Create account**.

### Updating
```bash
cd /opt/videodead
git pull
docker compose up -d --build api worker      # backend/UI changes
# or a full rebuild including the frontend:
sudo bash deploy.sh
```

---

## Enabling YouTube (per user)

YouTube blocks downloads from datacenter servers, so each user connects **their own** account once. In the app: click **Connect YouTube -> How?** and follow it:

1. Install the browser extension **"Get cookies.txt LOCALLY"**.
2. Sign in to `youtube.com` in that browser, export cookies in **Netscape** format.
3. In VideoDead, click **Connect YouTube** and pick that file.

The cookies are stored privately at `/data/usercookies/<user-id>/cookies.txt` and used only for that user's downloads.

**Behind the scenes**, three things make YouTube work from a server (all built into the image):
- the user's **cookies** (gets past "confirm you're not a bot"),
- **Node + Deno** (a JavaScript runtime to solve YouTube's "n-challenge"),
- yt-dlp option **`remote_components: ["ejs:github"]`** (lets yt-dlp fetch the challenge-solver script).

> yt-dlp is **pinned** to the version that works with this setup (currently `2026.6.9`). To update it later, bump the pin in `backend/requirements.txt` and `backend/Dockerfile`, rebuild, and re-test a YouTube link.

---

## Everyday operations

```bash
cd /opt/videodead
docker compose ps                  # what's running
docker compose logs -f worker      # live download logs
docker compose exec worker sh -c 'ls -la /downloads'   # staged files (should stay near-empty)
docker compose exec worker yt-dlp --version            # engine version
```

Clear any leftover files manually (rarely needed):
```bash
docker compose exec worker sh -c 'rm -rf /downloads/*'
```

---

## Troubleshooting

- **"Sign in to confirm you're not a bot" (YouTube):** that user hasn't connected their account, or their cookies expired. Re-export and re-upload via **Connect YouTube**.
- **"No downloadable format" / only storyboards (YouTube):** the JS-challenge engine isn't working. Confirm with
  `docker compose exec worker sh -c 'yt-dlp --cookies /data/usercookies/<uid>/cookies.txt --remote-components ejs:github -F "<url>"'` — you should see real formats (18, 22, 137...).
- **Site won't load / no certificate:** DNS isn't pointing at the droplet, or ports 80/443 are blocked. Check `docker compose logs caddy`.
- **A download fails on a link:** the site may be unsupported or DRM-protected (yt-dlp won't bypass DRM).

---

## Security

Secure-by-design per [CISA](https://www.cisa.gov/securebydesign) and Singapore CSA Safe App Standard 2.0. See [`SECURITY.md`](SECURITY.md). Highlights: HTTPS + HSTS, Argon2id passwords, optional TOTP, **per-user cookie isolation** (no shared accounts), SSRF guard, non-root hardened containers, files auto-deleted after download, minimal logging.

## Acceptable use

For content you own or have the right to download. Does **not** circumvent DRM. See [`ACCEPTABLE_USE.md`](ACCEPTABLE_USE.md).

## License

MIT — see [`LICENSE`](LICENSE).
