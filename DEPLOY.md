# Deploying VideoDead on your DigitalOcean droplet

You need three things, then one command.

## Before you start
- A droplet running Ubuntu (yours: `64.225.108.200`). Docker will be installed automatically if missing.
- A domain or subdomain you control (e.g. `videodead.example.com`).
- Ports **80** and **443** free. AmneziaVPN does not use them; nothing else should either.

## Step 1 — Point your domain at the droplet
In your DNS provider, add an **A record**:

```
Type: A    Name: videodead (or @)    Value: 64.225.108.200    TTL: 300
```

Wait a few minutes. Test from your PC: `ping videodead.example.com` should show `64.225.108.200`.

## Step 2 — Get the code onto the droplet
SSH in, then clone the repo (or `git pull` if it's already there):

```bash
ssh root@64.225.108.200
git clone https://github.com/feranicus/VideoDead.git /opt/videodead
cd /opt/videodead
```

## Step 3 — Run the deploy script
```bash
sudo bash deploy.sh
```

It will: install Docker if needed, ask for your **domain** and **email**, generate a strong secret,
build the web interface, and start everything. Caddy then fetches a free HTTPS certificate automatically.

## Step 4 — Open it and set your password
Go to `https://videodead.example.com`. The first screen asks you to create the admin password. Done.

## Everyday commands
```bash
cd /opt/videodead
docker compose ps           # what's running
docker compose logs -f      # live logs
docker compose restart      # restart
git pull && sudo bash deploy.sh   # update to the latest version
```

## If something's wrong
- **Site won't load / no certificate:** DNS isn't pointing at the droplet yet, or port 80/443 is blocked.
  Check `docker compose logs caddy` and confirm the A record.
- **"address already in use":** another service holds 80/443. Find it: `sudo ss -tlnp | grep -E ':80|:443'`.
- **DigitalOcean Cloud Firewall:** if you use one in the DO panel, allow inbound TCP 80 and 443.
- **Download fails on a link:** that site may be unsupported or protected (DRM). yt-dlp won't bypass DRM.

## Coexisting with AmneziaVPN
VideoDead only publishes 80/443. AmneziaVPN uses its own (different) ports, so the two run side by side
on the same droplet without conflict. Redis and the worker are not reachable from the internet at all.
