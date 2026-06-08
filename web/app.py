"""Flask web front-end for the lottery number generator.

Reuses the exact same :mod:`generator` and :mod:`utils` modules as the desktop
app. Serves a small single-page UI from ``static/`` and exposes a JSON API.

Run locally:

    pip install -r requirements.txt
    python app.py            # dev server on http://localhost:8000

In production it is served by gunicorn behind nginx (see docker-compose.yml).
"""
from __future__ import annotations

import hmac
import os
import sys

# Make the shared core modules (generator.py, utils.py) importable. They live
# one directory up in the source tree, and alongside this file inside Docker.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import (  # noqa: E402
    Flask,
    Response,
    g,
    jsonify,
    request,
    send_from_directory,
)

from generator import (  # noqa: E402
    MAX_SETS,
    PRESETS,
    CombinationGenerator,
    GenerationError,
    LotteryFormat,
)
from utils import combos_to_csv, format_combo  # noqa: E402

app = Flask(__name__, static_folder="static", static_url_path="")

# --------------------------------------------------------------------------- #
# Private-access gate (secret link)
# --------------------------------------------------------------------------- #
# Set ACCESS_TOKEN to make the site private. Anyone who opens
#     https://your-domain/?key=<ACCESS_TOKEN>
# is let in and gets a cookie so later requests work without the key.
# Leave ACCESS_TOKEN empty/unset to disable the gate (e.g. local development).
ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN", "").strip()
ACCESS_COOKIE = "lg_access"
COOKIE_MAX_AGE = 60 * 60 * 24 * 30  # 30 days
PUBLIC_PATHS = {"/api/health", "/robots.txt"}


def _token_ok(candidate: str) -> bool:
    """Constant-time comparison against the configured access token."""
    if not candidate or not ACCESS_TOKEN:
        return False
    return hmac.compare_digest(candidate, ACCESS_TOKEN)


def _denied() -> Response:
    body = (
        "<!doctype html><meta charset='utf-8'><title>Private</title>"
        "<body style='font-family:system-ui,sans-serif;text-align:center;"
        "margin-top:18vh;color:#555'>"
        "<h1 style='font-size:2rem'>&#128274; Private</h1>"
        "<p>This site is private. Open it with your access link.</p></body>"
    )
    resp = Response(body, status=401, mimetype="text/html")
    resp.headers["WWW-Authenticate"] = "Token realm=lottery"
    return resp


@app.before_request
def _enforce_access():
    if not ACCESS_TOKEN:
        return None  # gate disabled
    if request.path in PUBLIC_PATHS:
        return None
    # 1) Secret link ?key=TOKEN -> remember via cookie.
    if _token_ok(request.args.get("key", "")):
        g.set_access_cookie = True
        return None
    # 2) Header (handy for API/automation clients).
    if _token_ok(request.headers.get("X-Access-Token", "")):
        return None
    # 3) Previously issued cookie.
    if _token_ok(request.cookies.get(ACCESS_COOKIE, "")):
        return None
    return _denied()


@app.after_request
def _security_headers(resp: Response) -> Response:
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("X-Frame-Options", "DENY")
    resp.headers.setdefault("Referrer-Policy", "no-referrer")
    resp.headers.setdefault("X-Robots-Tag", "noindex, nofollow")
    if getattr(g, "set_access_cookie", False):
        secure = (
            request.is_secure
            or request.headers.get("X-Forwarded-Proto", "") == "https"
        )
        resp.set_cookie(
            ACCESS_COOKIE, ACCESS_TOKEN, max_age=COOKIE_MAX_AGE,
            httponly=True, samesite="Lax", secure=secure, path="/",
        )
    return resp


@app.get("/robots.txt")
def robots():
    # Keep the private site out of search engines entirely.
    return Response("User-agent: *\nDisallow: /\n", mimetype="text/plain")


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/api/health")
def health():
    return jsonify(status="ok")


@app.get("/api/presets")
def presets():
    return jsonify(
        presets=[
            {"name": f.name, "pick": f.pick, "max_number": f.max_number}
            for f in PRESETS.values()
        ],
        max_sets=MAX_SETS,
    )


def _parse_request(data: dict):
    """Validate and coerce the JSON body into (LotteryFormat, count, unique)."""
    try:
        pick = int(data.get("pick", 6))
        max_number = int(data.get("max_number", 49))
        count = int(data.get("count", 1))
    except (TypeError, ValueError):
        raise ValueError("pick, max_number and count must be whole numbers.")

    unique = bool(data.get("unique", False))

    if count < 1 or count > MAX_SETS:
        raise ValueError(f"Count must be between 1 and {MAX_SETS}.")

    # LotteryFormat raises ValueError for invalid pick/range combinations.
    fmt = LotteryFormat(name=f"{pick}/{max_number}", pick=pick, max_number=max_number)
    return fmt, count, unique


@app.post("/api/generate")
def generate():
    data = request.get_json(silent=True) or {}
    try:
        fmt, count, unique = _parse_request(data)
    except ValueError as exc:
        return jsonify(error=str(exc)), 400

    # A fresh generator per request keeps the service stateless; uniqueness is
    # therefore guaranteed within the returned batch.
    gen = CombinationGenerator(fmt)
    try:
        combos = gen.generate_many(count, unique=unique)
    except GenerationError as exc:
        return jsonify(error=str(exc)), 400

    pad = fmt.pad_width
    return jsonify(
        format=fmt.name,
        pad_width=pad,
        count=len(combos),
        sets=[
            {"numbers": combo, "formatted": format_combo(combo, pad)}
            for combo in combos
        ],
    )


@app.post("/api/export.csv")
def export_csv():
    """Return the supplied combinations as a downloadable CSV file."""
    data = request.get_json(silent=True) or {}
    sets = data.get("sets") or []
    if not sets:
        return jsonify(error="No sets to export."), 400
    pick = len(sets[0])
    payload = combos_to_csv(sets, pick)
    return (
        payload,
        200,
        {
            "Content-Type": "text/csv; charset=utf-8",
            "Content-Disposition": "attachment; filename=lottery.csv",
        },
    )


if __name__ == "__main__":
    # Development server only. Production uses gunicorn (see Dockerfile).
    app.run(host="0.0.0.0", port=8000, debug=True)
