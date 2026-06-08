# 🎲 Lottery Number Generator

Generate lottery-style number combinations with **cryptographically strong**
randomness (Python's `secrets` module — not `random`). Ships as **two
front-ends that share the same core engine**:

* a **Tkinter desktop app**, and
* a **Flask web app** ready to deploy with **Docker + nginx + Cloudflare**,
  optionally **private** (link-only access) and **bot-blocked**.

Each generated set has unique numbers, in **random (unsorted) positions**, e.g.

```
41 - 03 - 44 - 39 - 08 - 17
```

---

## Project structure

```
Number generator/
├── main.py              # desktop entry point
├── ui.py                # Tkinter UI (OOP, dark mode, copy/export)
├── generator.py         # shared core: secrets-based combination engine
├── utils.py             # shared core: formatting, validation, export
│
├── web/
│   ├── app.py           # Flask API + access gate + security headers
│   ├── requirements.txt
│   └── static/          # single-page UI (HTML/CSS/JS)
│
├── nginx/nginx.conf     # reverse proxy: bot block, rate limit, CF real-IP
├── Dockerfile           # gunicorn image for the web app
├── docker-compose.yml   # web + nginx (+ optional cloudflared tunnel)
└── .env.example         # ACCESS_TOKEN + TUNNEL_TOKEN
```

`generator.py` and `utils.py` are imported by **both** the desktop and web apps,
so there is a single source of truth for the lottery logic.

---

## 1) Desktop app (Tkinter)

Requires only the Python standard library (Python 3.10+).
Tkinter ships with CPython on Windows/macOS; on Debian/Ubuntu run
`sudo apt install python3-tk`.

```bash
python main.py
```

Features: format selector (6/49, 6/58, **Custom**), 1–1000 sets, **unique sets**
(no repeats per session), scrollable results, **Generate / Clear / Save TXT /
Export CSV / Copy all / Copy selected**, and a **dark-mode** toggle.

---

## 2) Web app — local dev

```bash
pip install -r web/requirements.txt
python web/app.py          # http://localhost:8000
```

JSON API:

| Method | Path             | Purpose                          |
|--------|------------------|----------------------------------|
| GET    | `/api/health`    | health check                     |
| GET    | `/api/presets`   | available formats + max sets     |
| POST   | `/api/generate`  | `{pick,max_number,count,unique}` |

---

## 3) Deploy with Docker + nginx

```bash
cp .env.example .env        # then edit .env
docker compose up -d --build
# open http://YOUR_SERVER:8080
```

`nginx` (port **8080**) reverse-proxies to `gunicorn` running the Flask app.
Change the host port by editing `ports:` in `docker-compose.yml`.

---

## 4) Make it private (link-only access)

Set `ACCESS_TOKEN` in `.env` to a long random value:

```bash
# Linux/macOS:           openssl rand -hex 24
# Windows PowerShell:    -join ((48..57+97..102) | Get-Random -Count 48 | % {[char]$_})
ACCESS_TOKEN=2f9c...long-random...e1
```

Now the site is **private**. Share **one link** with whoever should have access:

```
https://your-domain/?key=2f9c...long-random...e1
```

Opening it sets a 30-day cookie, so they stay in without re-entering the key.
Anyone without the link gets a **🔒 Private** page (HTTP 401). API clients can
send the token as the `X-Access-Token` header instead. Leave `ACCESS_TOKEN`
blank to make the site public again.

> The token is compared in constant time; the cookie is `HttpOnly` + `SameSite=Lax`
> (and `Secure` when served over HTTPS).

## 5) Block bots & outsiders

Handled by `nginx/nginx.conf` (no config needed):

* **Bot/automation user-agents blocked** (curl, wget, python-requests, scrapers,
  scanners like sqlmap/nmap/masscan…) and empty UAs → `403`.
* **Rate limiting** (10 r/s, burst 20) + connection limits per real client IP.
* **`noindex, nofollow`** header **+ `robots.txt: Disallow: /`** keep it out of
  search engines.
* **Security headers**: CSP, `X-Frame-Options: DENY`, `nosniff`, no-referrer.
* **Cloudflare real-IP** restored from `CF-Connecting-IP` so rate-limits key on
  the actual visitor.

For an extra layer on Cloudflare: enable **Bot Fight Mode** and (optionally) a
**WAF rate-limiting rule**, or put **Cloudflare Access** in front for identity-based
login. The app-level secret link works regardless of which you choose.

---

## 6) Publish through Cloudflare (Tunnel — no open ports)

Best fit for a personal server: expose the site via a **Cloudflare Tunnel**, so
you never open an inbound port.

1. Cloudflare dashboard → **Zero Trust → Networks → Tunnels → Create tunnel**.
2. Add a **public hostname** (e.g. `lottery.example.com`) pointing at the service
   URL **`http://nginx:80`**.
3. Copy the tunnel **token** into `.env` as `TUNNEL_TOKEN`.
4. Start everything including the tunnel:

```bash
docker compose --profile cloudflare up -d --build
```

`cloudflared` connects out to Cloudflare and serves your site at the hostname
over HTTPS. Keep port `8080` firewalled (or remove the `ports:` mapping) so the
**only** way in is through Cloudflare + your secret link.

---

## Security model in one line

**Cloudflare (TLS + bots) → nginx (bot UA block + rate limit + headers) →
Flask secret-link gate → app.** Layer as many of these as you like.
