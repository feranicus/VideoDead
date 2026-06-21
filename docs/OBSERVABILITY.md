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
