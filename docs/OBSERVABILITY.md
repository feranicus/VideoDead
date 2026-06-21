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
3. Open **`https://<your-domain>/observe`** and log in with the user/password above.
   The "VideoDead — Overview" dashboard (host CPU/RAM/disk, per-container CPU/memory,
   and a live logs panel) is already provisioned.

## Use it

- **Metrics:** open the **VideoDead — Overview** dashboard.
- **Logs:** the dashboard has a logs panel; or go to **Explore → Loki** and query
  e.g. `{container="videodead-worker-1"}` to read a single service's logs.
- **More dashboards (optional):** Dashboards → Import → enter ID **1860** (node-exporter
  full) or **193** (Docker) → select the Prometheus datasource.

## Security & access auditing (who did what)

Beyond infrastructure metrics, the app writes a structured **audit log** — one JSON
line per meaningful action — to stdout, which Promtail ships to Loki. A dedicated
dashboard, **"VideoDead — Security & Access"**, surfaces it in real time:

- **Who connected** — every sign-in with email, IP, and device/browser, plus the
  exact time. Sign-ups and sign-outs too.
- **Failed logins** — a stat tile (red above 8 in 1h) and a time chart. This is the
  main signal of credential-stuffing/brute force.
- **Links submitted** — every URL each user requested, with mode (video/audio).
- **Files downloaded & saved** — filename and size, logged the moment the user saves
  a file to their PC (which is also when the server deletes it).
- **Suspicious & blocked** — links that matched the piracy/illegal **watchlist**, plus
  SSRF-blocked and rate-limited attempts. Review these.

**Passwords are never logged.** They are one-way hashed (Argon2id); the audit trail
records *who/when/where/what* and authentication outcomes, not secrets. Any field that
looks like a password/secret/token is stripped before writing.

### Alerts (Grafana-only for now)
Two provisioned alert rules live under **Alerting → Alert rules** (folder *VideoDead*):

- **Failed login burst** — fires when >8 failed logins occur in 5 minutes.
- **Suspicious link flagged** — fires the instant a submitted link matches the watchlist.

They show in Grafana's Alerting UI today. To get phone/email pushes later, add a
**Contact point** (Telegram bot, email/SMTP, or a webhook to your Hermes+QWEN service)
and a notification policy — the rules already exist and will start routing to it.

### Tuning the "suspicious" watchlist
The default list flags common torrent/piracy/stream-ripping hosts. Add your own
without touching code via `/opt/videodead/.env`:
```
SUSPICIOUS_DOMAINS=examplepirate.com,badstream.net
```
Then `docker compose up -d --build api`. This is a heuristic **flag-and-alert**, not a
block — strict AI guardrails come in a later phase.

### Reading it directly
**Explore → Loki**, then:
```
{container=~"videodead-(api|worker)-1"} | json | log_type="audit"
```
Filter by event, e.g. `| event="suspicious.flagged"` or `| email="someone@example.com"`.

## Manage
```bash
docker compose --profile observe ps
docker compose --profile observe logs -f grafana
docker compose --profile observe down        # turn the whole stack off
```

## Notes
- Needs ~500 MB RAM; fine on a 2 GB droplet alongside the app. If you also run the
  optional YouTube `browser` profile at the same time, watch memory.
- Grafana has its own login; the page is served over your HTTPS. Change the password by
  editing `.env` and `docker compose --profile observe up -d` again.
- Logs are kept ~7 days (Loki retention) and metrics ~7 days (Prometheus retention).
