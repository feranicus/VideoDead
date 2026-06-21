# Monitoring & logs (Grafana / Prometheus / Loki)

VideoDead ships an optional, industry-standard observability stack you can turn on:

- **Grafana** — the dashboard UI (your login), at `https://<domain>/observe`
- **Prometheus** — metrics database
- **node-exporter** — host CPU / RAM / disk
- **cAdvisor** — per-container CPU / memory
- **Loki + Promtail** — collects and stores all container logs

It runs as a separate compose **profile**, so it never affects the core app.

## Turn it on

1. Set a Grafana password in `/opt/videodead/.env`:
   ```
   GRAFANA_USER=admin
   GRAFANA_PASSWORD=pick-a-strong-one
   ```
2. Start the stack:
   ```bash
   cd /opt/videodead
   docker compose --profile observe up -d
   ```
3. Open **`https://<your-domain>/observe`** and log in. Three dashboards are provisioned.

## The three dashboards

- **VideoDead — Overview** — infrastructure: host CPU/RAM/disk, per-container CPU/memory, live logs.
- **VideoDead — Security & Access** — who connected, failed logins, links submitted, files saved, suspicious/blocked.
- **VideoDead — Downloads & Errors** — the download pipeline (see below).

## Security & access auditing (who did what)

The app writes a structured **audit log** — one JSON line per meaningful action — to
stdout, which Promtail ships to Loki. The **Security & Access** dashboard surfaces it live:

- **Who connected** — every sign-in with email, IP, and device/browser, plus the exact time.
- **Failed logins** — a stat tile (red above 8 in 1h) and a time chart. Main brute-force signal.
- **Links submitted** — every URL each user requested, with mode (video/audio).
- **Files downloaded & saved** — filename and size, logged the moment the user saves a file.
- **Suspicious & blocked** — links matching the piracy/illegal watchlist, plus SSRF/rate-limit blocks.

**Passwords are never logged.** They are one-way hashed (Argon2id); the trail records
*who/when/where/what* and authentication outcomes, not secrets.

## Downloads & errors dashboard

The **Downloads & Errors** dashboard charts the download pipeline from the same audit log:

- Submitted vs **Completed** vs **Errors** (24h), and "Saved to a PC".
- **Data downloaded** and **average download time**.
- **Completions vs errors over time**, and **data/duration over time**.
- **Top error reasons** (grouped) and a live feed of **recent failures**.
- **Video vs Audio** split.

Use it to see at a glance whether downloads are succeeding and *why* any are failing.

## Alerts (Grafana-only for now)

Two provisioned rules live under **Alerting → Alert rules** (folder *VideoDead*):

- **Failed login burst** — >8 failed logins in 5 minutes.
- **Suspicious link flagged** — fires the instant a submitted link matches the watchlist.

To get phone/email pushes later, add a **Contact point** (Telegram, email/SMTP, or a
webhook to your Hermes+QWEN service) and a notification policy — the rules already exist.

## Tuning the "suspicious" watchlist

Add your own hosts without touching code, via `/opt/videodead/.env`:
```
SUSPICIOUS_DOMAINS=examplepirate.com,badstream.net
```
Then `docker compose up -d --build api`. This is a heuristic **flag-and-alert**, not a block.

## Reading the audit log directly

**Explore → Loki**, then:
```
{container=~"videodead-(api|worker)-1"} | json | log_type="audit"
```
Filter by event, e.g. `| event="download.error"` or `| email="someone@example.com"`.

## Manage
```bash
docker compose --profile observe ps
docker compose --profile observe logs -f grafana
docker compose --profile observe down        # turn the whole stack off
```

## Notes
- Needs ~1 GB RAM with the full stack; comfortable on the 4 GB droplet alongside the app.
- Grafana has its own login; served over your HTTPS at `/observe`. Change the password by
  editing `.env` and `docker compose --profile observe up -d` again.
- Logs are kept ~7 days (Loki retention) and metrics ~7 days (Prometheus retention).
