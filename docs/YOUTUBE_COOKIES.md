# Enabling YouTube downloads (cookies)

YouTube blocks downloads coming from datacenter servers with *"Sign in to confirm you're not
a bot."* The fix is to give the server a `cookies.txt` from a logged-in YouTube session.
VideoDead uses it automatically if the file is present, and ignores it if not.

> **Use a THROWAWAY Google account**, never your personal one. Accounts used for downloads
> from a server can get rate-limited or locked by Google. Cookies also expire — expect to
> repeat this every few weeks.

## 1. Export cookies.txt from a browser

1. In Chrome or Firefox, install the open-source extension **"Get cookies.txt LOCALLY"**.
2. Open a **private/incognito window** and sign in to `https://youtube.com` with your throwaway account.
3. Open one normal video once so the session is fully established.
4. Click the extension → **Export** → save the file as `cookies.txt` (Netscape format, for `youtube.com`).
5. Close that private window and don't reuse it — YouTube rotates cookies, and reusing the
   session can invalidate the file you just exported.

## 2. Put it on the server

From your PC (replace the IP if needed):

```
scp cookies.txt root@64.225.108.200:/opt/videodead/secrets/cookies.txt
```

The `secrets/` folder is mounted read-only into the worker at `/secrets`, and is git-ignored
so it never lands in your repository.

## 3. Apply it

On the droplet:

```
cd /opt/videodead
docker compose restart worker
```

## 4. Test

Paste a YouTube link in the website and press Download. If it still says it's blocked, the
cookies likely expired or the account got flagged — repeat step 1 with a fresh export.

## Notes
- Nothing about the doctor's experience changes — she just pastes links. The cookies work
  silently in the background.
- This does **not** bypass DRM or paid content; it only proves to YouTube that the request
  comes from a real signed-in session.
- If YouTube reliability matters a lot, the more robust (paid) alternative is routing the
  worker's traffic through a residential proxy — ask and we can add that later.
