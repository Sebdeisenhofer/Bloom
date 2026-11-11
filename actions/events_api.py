"""Tiny JSON API so neighbors can share events from the Bloom website.

Events are stored in the same SQLite database the Rasa action server uses,
so anything posted here is also searchable by the "Ask Bloom" assistant.

    GET    /api/events            -> community-posted events (today or later)
    POST   /api/events            -> create an event (JSON body)
    DELETE /api/events/<id>?user= -> remove an event you posted
    GET    /api/health            -> {"ok": true}
"""

import json
import re
from datetime import date, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from actions.actions import connect, initialize_database

PORT = 5056
AREAS = {"downtown", "west", "south", "northeast", "east", "keizer"}
GROUPS = {"small", "large"}
NEEDS = {"accessible", "seating", "hearing", "free", "bus", "parking"}
TIME_RE = re.compile(r"^(1[0-2]|[1-9]):[0-5]\d (AM|PM)$")


def migrate() -> None:
    initialize_database()  # creates tables and community-event columns


def clean(value, limit: int) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()[:limit]


def validate(body: dict) -> tuple[dict | None, str]:
    title = clean(body.get("title"), 90)
    location = clean(body.get("location"), 140)
    description = clean(body.get("description"), 800)
    host = clean(body.get("host"), 80)
    time = clean(body.get("time"), 8)
    user = clean(body.get("user"), 80)
    if not title:
        return None, "Please give your event a name."
    if not location:
        return None, "Please say where the event is."
    if not TIME_RE.match(time):
        return None, "Please choose a start time."
    try:
        day = date.fromisoformat(clean(body.get("date"), 10))
    except ValueError:
        return None, "Please choose a date."
    if day < date.today():
        return None, "That date has already passed."
    tags = [t for t in (clean(t, 20) for t in body.get("tags") or []) if re.fullmatch(r"[a-z]+", t)][:6]
    area = body.get("area") if body.get("area") in AREAS else ""
    group = body.get("group") if body.get("group") in GROUPS else "small"
    needs = [n for n in body.get("needs") or [] if n in NEEDS]
    return {
        "title": title,
        "date": day.isoformat(),
        "time": time,
        "location": location,
        "category": clean(body.get("category"), 40) or "Community",
        "tags": ", ".join(tags) or "community",
        "group_size": group,
        "description": description or "A community event shared by a neighbor.",
        "host": host or "A Bloom neighbor",
        "area": area,
        "cost": clean(body.get("cost"), 60) or "Free",
        "needs": ", ".join(needs),
        "created_by": user or "anonymous",
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }, ""


def to_json(row) -> dict:
    r = dict(row)
    return {
        "id": r["id"],
        "title": r["title"],
        "date": r["date"],
        "time": r["time"],
        "place": r["location"],
        "area": r.get("area") or "",
        "tags": [t.strip() for t in (r.get("tags") or "").split(",") if t.strip()],
        "group": r.get("group_size") or "small",
        "cost": r.get("cost") or "Free",
        "needs": [n.strip() for n in (r.get("needs") or "").split(",") if n.strip()],
        "host": r["host"],
        "desc": r["description"],
        "createdBy": r.get("created_by") or "",
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "BloomEvents/1.0"

    def send(self, status: int, payload) -> None:
        data = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        path = urlparse(self.path).path.rstrip("/")
        if path == "/api/health":
            return self.send(200, {"ok": True})
        if path != "/api/events":
            return self.send(404, {"error": "Not found"})
        with connect() as db:
            rows = db.execute(
                "SELECT * FROM events WHERE created_by IS NOT NULL AND date >= ? ORDER BY date, time",
                (date.today().isoformat(),),
            ).fetchall()
        self.send(200, {"events": [to_json(r) for r in rows]})

    def do_POST(self) -> None:
        if urlparse(self.path).path.rstrip("/") != "/api/events":
            return self.send(404, {"error": "Not found"})
        try:
            length = min(int(self.headers.get("Content-Length") or 0), 20_000)
            body = json.loads(self.rfile.read(length) or b"{}")
            if not isinstance(body, dict):
                raise ValueError
        except ValueError:
            return self.send(400, {"error": "Something went wrong reading that. Please try again."})
        event, problem = validate(body)
        if problem:
            return self.send(400, {"error": problem})
        cols = ", ".join(event)
        marks = ", ".join("?" for _ in event)
        with connect() as db:
            cursor = db.execute(f"INSERT INTO events ({cols}) VALUES ({marks})", tuple(event.values()))
            row = db.execute("SELECT * FROM events WHERE id = ?", (cursor.lastrowid,)).fetchone()
        self.send(201, {"event": to_json(row)})

    def do_DELETE(self) -> None:
        parsed = urlparse(self.path)
        match = re.fullmatch(r"/api/events/(\d+)", parsed.path.rstrip("/"))
        user = (parse_qs(parsed.query).get("user") or [""])[0]
        if not match or not user:
            return self.send(404, {"error": "Not found"})
        with connect() as db:
            cursor = db.execute(
                "DELETE FROM events WHERE id = ? AND created_by = ?", (int(match.group(1)), user)
            )
            if cursor.rowcount:
                db.execute("DELETE FROM rsvps WHERE event_id = ?", (int(match.group(1)),))
        self.send(200 if cursor.rowcount else 403, {"deleted": bool(cursor.rowcount)})

    def log_message(self, fmt, *args) -> None:  # quieter logs
        print("events-api:", fmt % args, flush=True)


def main() -> None:
    migrate()
    print(f"Bloom events API listening on :{PORT}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
