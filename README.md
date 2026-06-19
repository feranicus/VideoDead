# VideoDead

A dead-simple, secure-by-design web app to download streaming video and audio from any **lawful** source. One screen: paste a link, choose **Video** or **Audio only**, click **Download**.

Built on the [yt-dlp](https://github.com/yt-dlp/yt-dlp) engine. Hosted on a single DigitalOcean droplet with Docker Compose. Designed for a non-technical end user — no install, just a bookmarked HTTPS URL.

> See [`docs/HLD.html`](docs/HLD.html) for the full high-level design (architecture, stack rationale, threat model, secure-by-design controls).

## Architecture (at a glance)

```
Internet ──HTTPS──> Caddy (edge, auto-TLS, headers)
                      ├── serves React SPA (static)
                      └── /api ──> FastAPI ──enqueue──> Redis ──> Worker (arq + yt-dlp) ──> /downloads
                                       └── SQLite (user + job history)
```

Four containers: `caddy`, `api`, `worker`, `redis`. See `docker-compose.yml`.

## Tech stack

| Layer | Choice | Why |
|-------|--------|-----|
| Frontend | React + Vite + TypeScript + Tailwind | Fast, type-safe, easy one-screen UI |
| API | Python 3.12 + FastAPI | yt-dlp is Python → call as a library, no shelling out |
| Worker | arq + Redis | Long downloads run off the web request |
| State | Redis + SQLite | Queue/sessions in Redis, user/history in one SQLite file |
| Edge | Caddy | Automatic HTTPS + security headers, one-line config |
| Runtime | Docker Compose / Ubuntu 26.04 | One droplet, one-command deploy |

## Quick start (local dev)

```bash
cp .env.example .env          # set ADMIN_EMAIL, SESSION_SECRET, DOMAIN
docker compose up --build     # api, worker, redis, caddy
# open https://localhost (accept the dev cert) and complete the first-run wizard
```

Backend only, without Docker:

```bash
cd backend
python -m venv .venv && . .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
# worker, separate terminal:
arq app.worker.WorkerSettings
```

Frontend only:

```bash
cd frontend
npm install
npm run dev
```

## Deploy to DigitalOcean

1. Create an Ubuntu 26.04 droplet, install Docker + Compose.
2. Point a domain's A record at the droplet IP.
3. Copy the repo, set `.env` (`DOMAIN`, `ADMIN_EMAIL`, `SESSION_SECRET`).
4. `docker compose up -d` — Caddy provisions HTTPS automatically.
5. Open the site and complete the one-time secure-password wizard.

CI/CD is in `.github/workflows/` (test, CodeQL, Trivy, SBOM, build, deploy).

## Security

Secure-by-design per CISA and Singapore CSA Safe App Standard 2.0. See [`SECURITY.md`](SECURITY.md) and the controls table in the HLD. Report vulnerabilities per `SECURITY.md`.

## Acceptable use

For content you own or have the right to download. Does **not** circumvent DRM. See [`ACCEPTABLE_USE.md`](ACCEPTABLE_USE.md).

## License

MIT — see [`LICENSE`](LICENSE).
