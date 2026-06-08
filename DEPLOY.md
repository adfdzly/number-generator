# Deploy → https://num-genator.aefoxlab.uk

Private site, link-only access, published through a Cloudflare Tunnel
(no inbound ports open on your server).

> Domain spelling used everywhere below: **num-genator.aefoxlab.uk**
> (exactly as you gave it — fix here + `nginx/nginx.conf` if it should be
> `num-generator`).

---

## Prerequisites

* `aefoxlab.uk` is added to Cloudflare (its nameservers point to Cloudflare).
* Docker + Docker Compose on the server.

---

## 1. Create the Cloudflare Tunnel

1. Cloudflare dashboard → **Zero Trust → Networks → Tunnels → Create a tunnel**
   → connector **Cloudflared** → name it (e.g. `num-genator`).
2. Copy the **tunnel token** (the long string after `--token`).
3. **Public Hostnames → Add a public hostname:**
   * **Subdomain:** `num-genator`
   * **Domain:** `aefoxlab.uk`
   * **Type:** `HTTP`
   * **URL:** `nginx:80`
   Cloudflare auto-creates the proxied DNS record for `num-genator.aefoxlab.uk`.

---

## 2. Configure secrets on the server

```bash
cd "Number generator"
cp .env.example .env
```

Edit `.env`:

```env
# strong private key  (Linux/macOS: openssl rand -hex 24)
ACCESS_TOKEN=PUT-A-LONG-RANDOM-STRING-HERE

# paste the tunnel token from step 1
TUNNEL_TOKEN=eyJhIjoixxxxxxxx...
```

---

## 3. Launch (web + nginx + tunnel)

```bash
docker compose --profile cloudflare up -d --build
```

Check:

```bash
docker compose ps
docker compose logs -f cloudflared    # should say "Registered tunnel connection"
```

Site is now live at **https://num-genator.aefoxlab.uk**.

---

## 4. The access link to share

```
https://num-genator.aefoxlab.uk/?key=<ACCESS_TOKEN>
```

Opening it sets a 30-day cookie; after that the bare domain works.
Anyone without the link gets a **🔒 Private** page.

---

## 5. Recommended Cloudflare toggles (dashboard)

* **SSL/TLS → Overview:** Full or Full (strict) → **Always Use HTTPS: On**
  (so the secure cookie sticks).
* **Security → Bots:** **Bot Fight Mode: On**.
* (Optional, stronger) **Zero Trust → Access** in front of the hostname for
  identity-based login on top of the secret link.

Keep the host port `8080` firewalled (or delete the `ports:` mapping in
`docker-compose.yml`) so the **only** way in is the tunnel + your key.

---

## Update / restart later

```bash
git pull        # if versioned
docker compose --profile cloudflare up -d --build
```
