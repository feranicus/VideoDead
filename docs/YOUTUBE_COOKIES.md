# YouTube — automatic cookies (Chromium engine)

YouTube blocks downloads from datacenter servers unless the request carries cookies from a
logged-in session. VideoDead can do this **automatically**: a Chromium browser runs on the
droplet, stays logged in to a YouTube account, and an exporter feeds fresh cookies to the
worker on a schedule. After one human login, there is **no manual work** — the doctor and
other users just paste links.

> Use a **throwaway Google account**, never a personal one. Accounts used from a server can be
> rate-limited or locked by Google.

## One-time setup

### 1. Set a browser password
In `/opt/videodead/.env` add (or edit):

```
BROWSER_USER=admin
BROWSER_PASSWORD=pick-a-strong-one
```

### 2. Start the optional YouTube stack
```
cd /opt/videodead
docker compose --profile youtube up -d --build
```
This launches `browser` (Chromium) and `cookie-exporter`. The browser's login screen is bound
to **localhost only** for safety — you reach it through an SSH tunnel.

### 3. Open the browser UI through an SSH tunnel
From your PC:

```
ssh -L 3010:127.0.0.1:3010 root@64.225.108.200
```

Leave that window open, then in your local browser go to:

```
http://localhost:3010
```

Enter the `BROWSER_USER` / `BROWSER_PASSWORD` you set. You'll see a real Chromium desktop.

### 4. Log into YouTube once
In that Chromium, go to `youtube.com`, sign in with the throwaway Google account, and complete
any 2-step verification. That's the only manual step, ever. The login persists.

### Done
Within a few minutes the exporter writes cookies and the worker starts using them automatically.
Paste a YouTube link in the website to confirm. Cookies refresh on their own every
`EXPORT_INTERVAL` seconds.

## Managing it
```
docker compose --profile youtube ps                 # status
docker compose logs -f cookie-exporter              # see exports
docker compose --profile youtube restart browser    # if login gets stuck
docker compose --profile youtube down               # turn the whole thing off
```

## Notes
- The core app does **not** depend on this — if the browser stack is off, everything else works;
  only YouTube needs it.
- A manual `secrets/cookies.txt` (old method) still works as a fallback if you ever prefer it.
- This does not bypass DRM; it only proves a real signed-in session to YouTube.
- Truly zero-login alternative = a residential proxy (paid); ask and we can add it.
