"""Tiny JSON API so neighbors can share events from the Bloom website.

Events are stored in the same SQLite database the Rasa action server uses,
so anything posted here is also searchable by the "Ask Bloom" assistant.

    GET    /api/events                -> real (imported) + community-posted events, today onward
    POST   /api/events                -> create an event (JSON body; poster needs a profile name)
    DELETE /api/events/<id>?user=     -> remove an event you posted
    POST   /api/events/<id>/report    -> flag a community event; hidden after REPORT_LIMIT reports
    POST   /api/profile               -> save {user, name, email}; email is never returned publicly
    GET    /api/health                -> {"ok": true}
"""

import json
import os
import re
import threading
import time as clock_time
from datetime import date, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from actions.actions import connect, initialize_database
from actions import real_events

REFRESH_HOURS = float(os.environ.get("REAL_EVENTS_REFRESH_HOURS", "3"))

PORT = 5056
AREAS = {"downtown", "west", "south", "northeast", "east", "keizer"}
GROUPS = {"small", "large"}
NEEDS = {"accessible", "seating", "hearing", "free", "bus", "parking"}
TIME_RE = re.compile(r"^(1[0-2]|[1-9]):[0-5]\d (AM|PM)$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
REPORT_LIMIT = 3  # community events with this many reports are hidden until reviewed


def migrate() -> None:
    initialize_database()  # creates tables and community-event columns
    with connect() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS members (
                user_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS reports (
                event_id INTEGER NOT NULL,
                user_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY (event_id, user_id)
            );
            """
        )


def member(db, user: str):
    return db.execute("SELECT * FROM members WHERE user_id = ?", (user,)).fetchone() if user else None


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
        "source": "community",
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }, ""


def to_json(row) -> dict:
    r = dict(row)
    return {
        "id": r["id"],
        "title": r["title"],
        "date": r["date"],
        "time": r["time"],
        "endTime": r.get("end_time") or "",
        "place": r["location"],
        "area": r.get("area") or "",
        "tags": [t.strip() for t in (r.get("tags") or "").split(",") if t.strip()],
        "group": r.get("group_size") or "small",
        "cost": r.get("cost") or "Free",
        "needs": [n.strip() for n in (r.get("needs") or "").split(",") if n.strip()],
        "host": r["host"],
        "desc": r["description"],
        "createdBy": r.get("created_by") or "",
        "posterName": r.get("poster_name") or "",
        "posterEvents": r.get("poster_events") or 0,
        "source": r.get("source") or ("community" if r.get("created_by") else "sample"),
        "url": r.get("url") or "",
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

    def read_json(self) -> dict | None:
        try:
            length = min(int(self.headers.get("Content-Length") or 0), 20_000)
            body = json.loads(self.rfile.read(length) or b"{}")
            return body if isinstance(body, dict) else None
        except ValueError:
            return None

    def do_GET(self) -> None:
        path = urlparse(self.path).path.rstrip("/")
        if path == "/api/health":
            return self.send(200, {"ok": True})
        if path != "/api/events":
            return self.send(404, {"error": "Not found"})
        with connect() as db:
            rows = db.execute(
                "SELECT e.*, m.name AS poster_name, "
                "  (SELECT COUNT(*) FROM events p WHERE p.created_by = e.created_by) AS poster_events "
                "FROM events e LEFT JOIN members m ON m.user_id = e.created_by "
                "WHERE (e.created_by IS NOT NULL OR e.source NOT IN ('', 'community')) AND e.date >= ? "
                "  AND (SELECT COUNT(*) FROM reports r WHERE r.event_id = e.id) < ? "
                "ORDER BY e.date, e.time",
                (date.today().isoformat(), REPORT_LIMIT),
            ).fetchall()
        events = [to_json(r) for r in rows]
        self.send(200, {"events": events, "real": any(e["source"] not in ("community", "sample") for e in events)})

    def do_POST(self) -> None:
        path = urlparse(self.path).path.rstrip("/")
        body = self.read_json()
        if body is None:
            return self.send(400, {"error": "Something went wrong reading that. Please try again."})
        if path == "/api/profile":
            return self.save_profile(body)
        report = re.fullmatch(r"/api/events/(\d+)/report", path)
        if report:
            return self.report_event(int(report.group(1)), clean(body.get("user"), 80))
        if path != "/api/events":
            return self.send(404, {"error": "Not found"})
        event, problem = validate(body)
        if problem:
            return self.send(400, {"error": problem})
        cols = ", ".join(event)
        marks = ", ".join("?" for _ in event)
        with connect() as db:
            poster = member(db, event["created_by"])
            if not poster:
                return self.send(400, {"error": "Please add your name in My profile before posting, so neighbors know who is hosting."})
            if event["host"] == "A Bloom neighbor":
                event["host"] = poster["name"]
            cursor = db.execute(f"INSERT INTO events ({cols}) VALUES ({marks})", tuple(event.values()))
            row = db.execute("SELECT * FROM events WHERE id = ?", (cursor.lastrowid,)).fetchone()
        self.send(201, {"event": to_json(row)})

    def save_profile(self, body: dict) -> None:
        user, name, email = clean(body.get("user"), 80), clean(body.get("name"), 60), clean(body.get("email"), 120)
        if not user:
            return self.send(400, {"error": "Missing user."})
        if not name:
            return self.send(400, {"error": "Please enter your name."})
        if email and not EMAIL_RE.match(email):
            return self.send(400, {"error": "That email doesn’t look quite right. Please check it."})
        with connect() as db:
            db.execute(
                "INSERT INTO members (user_id, name, email, updated_at) VALUES (?, ?, ?, ?) "
                "ON CONFLICT(user_id) DO UPDATE SET name = excluded.name, email = excluded.email, updated_at = excluded.updated_at",
                (user, name, email, datetime.now().isoformat(timespec="seconds")),
            )
            db.execute("UPDATE events SET host = ? WHERE created_by = ? AND host = 'A Bloom neighbor'", (name, user))
        self.send(200, {"ok": True, "name": name})

    def report_event(self, event_id: int, user: str) -> None:
        if not user:
            return self.send(400, {"error": "Missing user."})
        with connect() as db:
            row = db.execute("SELECT created_by FROM events WHERE id = ? AND source = 'community'", (event_id,)).fetchone()
            if not row:
                return self.send(404, {"error": "Only events shared by neighbors can be reported."})
            if row["created_by"] != user:
                db.execute(
                    "INSERT OR IGNORE INTO reports (event_id, user_id, created_at) VALUES (?, ?, ?)",
                    (event_id, user, datetime.now().isoformat(timespec="seconds")),
                )
            count = db.execute("SELECT COUNT(*) FROM reports WHERE event_id = ?", (event_id,)).fetchone()[0]
        self.send(200, {"reported": True, "hidden": count >= REPORT_LIMIT})

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


def refresh_forever() -> None:
    while True:
        try:
            real_events.refresh()
        except Exception as error:  # never let the importer take the API down
            print(f"events-api: refresh failed: {error}", flush=True)
        clock_time.sleep(REFRESH_HOURS * 3600)


def main() -> None:
    migrate()
    threading.Thread(target=refresh_forever, daemon=True).start()
    print(f"Bloom events API listening on :{PORT}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
