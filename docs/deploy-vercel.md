# Putting Bloom online (Vercel + backend)

Bloom has two halves:

| Part | What it is | Where it can run |
| --- | --- | --- |
| Website (`web/`) | Static HTML, CSS and JS | **Vercel** (free) |
| Backend (`docker compose`) | Rasa Pro, action server, events API, SQLite | Any machine with Docker: your laptop, or a cloud VM |

Vercel only hosts static sites and short serverless functions. It cannot run
Rasa Pro, which is a long-running container that needs about 2–4 GB of RAM and
the license key. So Vercel serves the website, and `vercel.json` forwards
`/api/*` (events) and `/webhooks/*` (chat) to wherever the backend runs. The
browser only ever talks to the Vercel URL.

If the backend is offline, the Vercel site still loads, but it falls back to
sample events and the chat says it can't connect.

## 1. Push the code to GitHub

```bash
git add -A
git commit -m "Add Willamette events, adult relevance filter, end times, Vercel config"
git push
```

`.env` (the Rasa license) is in `.gitignore` and must never be pushed.

## 2. Give the backend a public HTTPS address

### Option A: from your laptop (free, quickest; good for a demo day)

```bash
docker compose up -d --build          # backend + web on http://localhost:8081
brew install cloudflared              # one time
cloudflared tunnel --url http://localhost:8081
```

`cloudflared` prints a URL like `https://random-words.trycloudflare.com`. Keep
that terminal open: the link only works while your laptop is awake and the
tunnel is running. A quick tunnel gets a **new URL each time**, so redo
step 3 whenever you restart it.

### Option B: an always-on cloud VM (for a link that keeps working)

1. Create an Ubuntu VM with **at least 4 GB RAM**. For example, a DigitalOcean
   droplet (the GitHub Student Developer Pack includes credit).
2. Install Docker, then run:
   ```bash
   git clone https://github.com/sebastiandeisenhofer/bloom.git && cd bloom
   cp .env.example .env && nano .env      # paste RASA_PRO_LICENSE here, on the server only
   docker compose up -d --build
   ```
3. Give it HTTPS: run `cloudflared tunnel --url http://localhost:8081` on the
   VM as above, or set up a named Cloudflare Tunnel or Caddy with your own
   domain so the URL never changes.

## 3. Point Vercel at the backend

In `vercel.json`, replace both `REPLACE-WITH-YOUR-BACKEND-URL` with the host
from step 2, with no `https://` and no trailing slash. For example:

```json
{ "source": "/api/:path*", "destination": "https://random-words.trycloudflare.com/api/:path*" }
```

Commit and push.

## 4. Create the Vercel project

1. Go to <https://vercel.com>, sign in with GitHub, then **Add New → Project**.
2. Import the `bloom` repository.
3. Use these settings (`vercel.json` already sets them):
   - Framework preset: **Other**
   - Build command: *(empty)*
   - Output directory: **web**
4. Click **Deploy**. You get a live link like `https://bloom-xxxx.vercel.app`.
   You can rename it under **Settings → Domains**.

Every `git push` redeploys the site automatically.

## 5. Check it

- `https://<your-site>.vercel.app/api/health` should return `{"ok": true}`.
- The home page note should say "Real upcoming events from Salem Public
  Library, Willamette University athletics…".
- Open **Ask Bloom** and type "What's on this week?".

If the health check fails, the backend or tunnel isn't running, or the URL in
`vercel.json` is out of date.
