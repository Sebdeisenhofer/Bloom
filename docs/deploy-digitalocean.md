# Bloom on DigitalOcean (always-on public link)

This runs the whole app (website, Rasa agent, actions and events) on one small
server, 24/7, with HTTPS. Nobody's laptop needs to be on.

```
Internet ──HTTPS──▶ Caddy (80/443) ──▶ nginx "web" ──▶ /webhooks/ → Rasa ──▶ action server
                                                    └─▶ /api/      → events API ─┘ (shared SQLite)
```

Only Caddy is reachable from the internet. Rasa's own API is not exposed.

## 1. Create the droplet (about 5 minutes)

1. Students: claim DigitalOcean credit through the
   [GitHub Student Developer Pack](https://education.github.com/pack).
2. In DigitalOcean, choose **Create → Droplets**:
   - **Region:** San Francisco (closest to Salem)
   - **Image:** Ubuntu 24.04 LTS
   - **Size:** Basic, Regular, **4 GB RAM / 2 CPUs** (about $24/mo).
     A 2 GB droplet also works, but the first start is slower.
   - **Authentication:** SSH key (recommended) or a password
3. Click **Create Droplet** and copy its **IPv4 address**.

## 2. Install Bloom (about 10 minutes, mostly waiting)

Open a terminal on your computer, then:

```bash
ssh root@YOUR_DROPLET_IP
git clone https://github.com/Sebdeisenhofer/Bloom.git /opt/bloom
bash /opt/bloom/deploy/setup-server.sh
```

The script asks for your **Rasa Pro license**. Paste it and press Enter; the
input is hidden. The license is saved only on the server, in `/opt/bloom/.env`.

The script then installs Docker, starts everything and trains the Rasa model,
and finishes by printing your link:

```
Bloom is live at:  https://203-0-113-7.sslip.io
```

`sslip.io` is a free service that turns your server's IP into a web address,
so HTTPS works without buying a domain. Share that link with anyone.

## 3. Check it

- `https://<your-link>/api/health` shows `{"ok": true}`
- The home page shows real Salem events
- **Ask Bloom → "What's on this week?"** answers. This is the Rasa agent.

## Updating after you push changes to GitHub

```bash
ssh root@YOUR_DROPLET_IP
bash /opt/bloom/deploy/update.sh             # website, actions, event sources
bash /opt/bloom/deploy/update.sh --retrain   # if data/flows.yml, domain.yml or config.yml changed
```

## Useful commands (on the server)

```bash
cd /opt/bloom
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps            # status
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f rasa  # Rasa logs
docker compose -f docker-compose.yml -f docker-compose.prod.yml restart       # restart all
```

Everything restarts by itself if the droplet reboots.

## Optional: your own domain

Point an `A` record (for example `bloom.yourdomain.com`) at the droplet IP. Set
`BLOOM_DOMAIN=bloom.yourdomain.com` in `/opt/bloom/.env`, then run `update.sh`.
Caddy gets a new certificate automatically.

## Notes

- **Cost:** a droplet is billed while it exists, even when it's powered off.
  **Destroy** it after the class to stop charges.
- **Chat reliability:** the agent uses Rasa's free shared tutorial AI
  (`endpoints.yml`), which is sometimes overloaded. For a dependable public
  demo, switch to your own LLM key.
- **Moderation:** anyone with the link can post an event. Check the board
  before presenting.
