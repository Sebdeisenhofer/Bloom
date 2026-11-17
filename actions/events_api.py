"""Tiny JSON API so neighbors can share events from the Bloom website.

Events are stored in the same SQLite database the Rasa action server uses,
so anything posted here is also searchable by the "Ask Bloom" assistant.

    GET    /api/events                -> real (imported) + community-posted events, today onward
    POST   /api/events                -> create an event (signed-in accounts only)
    DELETE /api/events/<id>           -> remove an event you posted (signed in)
    POST   /api/events/<id>/report    -> flag a community event; hidden after REPORT_LIMIT reports
    POST   /api/register              -> {email, name, password, profile?} -> {token, user}
    POST   /api/login                 -> {email, password} -> {token, user}
    POST   /api/logout                -> end this session
    GET    /api/me                    -> the signed-in account (profile, saved events)
    PUT    /api/me                    -> save {profile?, saved?}
    GET    /api/saved?owner=          -> event ids this person saved (guest id or signed-in account)
    POST   /api/saved                 -> {owner, event_id} save an event; DELETE /api/saved/<id>?owner= removes it
    POST   /api/saved/merge           -> {from: guest_id} move a guest's saved events into the signed-in account
    GET    /api/community?owner=      -> community posts (meetups, interest groups) with joins and comments
    POST   /api/community             -> new post (signed in); POST /api/community/<id>/join toggles joining
    POST   /api/community/<id>/comments -> add a comment (signed in); DELETE /api/community/<id> removes your post
    GET    /api/health                -> {"ok": true}

Authentication: "Authorization: Bearer <token>". Passwords are stored as salted
PBKDF2-SHA256 hashes; emails are never returned in public event data.
"""

import hashlib
import hmac
import json
import os
import re
import secrets
import threading
import uuid
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
USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{3,30}$")
PBKDF2_ROUNDS = 200_000
DEMO_PROFILE = {
    "name": "Margaret", "email": "", "interests": ["gardening", "books", "fitness", "social"], "area": "south",
    "distance": "town", "transport": ["bus"], "days": ["Tue", "Wed", "Thu"], "times": ["morning", "afternoon"],
    "group": "small", "needs": ["seating", "free"], "notes": "", "completed": True,
}
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
            CREATE TABLE IF NOT EXISTS accounts (
                user_id TEXT PRIMARY KEY,
                username TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                profile_json TEXT NOT NULL DEFAULT '{}',
                saved_json TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY,
                user_id TEXT NOT NULL,
                category TEXT NOT NULL,
                title TEXT NOT NULL,
                body TEXT NOT NULL DEFAULT '',
                schedule TEXT NOT NULL DEFAULT '',
                place TEXT NOT NULL DEFAULT '',
                is_sample INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS post_joins (
                post_id INTEGER NOT NULL,
                owner TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY (post_id, owner)
            );
            CREATE TABLE IF NOT EXISTS post_comments (
                id INTEGER PRIMARY KEY,
                post_id INTEGER NOT NULL,
                user_id TEXT NOT NULL,
                body TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )
        existing = {row["name"] for row in db.execute("PRAGMA table_info(accounts)")}
        for name in ("email", "name"):
            if name not in existing:
                db.execute(f"ALTER TABLE accounts ADD COLUMN {name} TEXT NOT NULL DEFAULT ''")
        # Older username-only accounts: their username doubles as the sign-in name.
        db.execute("UPDATE accounts SET email = lower(username) WHERE email = '' AND username LIKE '%@%'")
        # Ready-made demo account for presentations: demo@bloom.local / demo (username "demo" works too).
        if not db.execute("SELECT 1 FROM accounts WHERE username = 'demo'").fetchone():
            create_account(db, "demo", "demo", DEMO_PROFILE, [], email="demo@bloom.local", name="Margaret")
        db.execute("UPDATE accounts SET email = 'demo@bloom.local', name = 'Margaret' WHERE username = 'demo' AND email = ''")


COMMUNITY_CATEGORIES = {
    "language", "books", "gardening", "crafts", "walking", "fitness", "games", "music", "cooking", "faith",
    "volunteering", "learning", "tech", "history", "social", "other",
}


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def hash_password(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), PBKDF2_ROUNDS).hex()


def create_account(db, username: str, password: str, profile: dict, saved: list, email: str = "", name: str = "") -> str:
    user_id = "acct-" + uuid.uuid4().hex
    salt = secrets.token_hex(16)
    db.execute(
        "INSERT INTO accounts (user_id, username, password_hash, salt, profile_json, saved_json, created_at, email, name) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (user_id, username, hash_password(password, salt), salt, json.dumps(profile), json.dumps(saved),
         datetime.now().isoformat(timespec="seconds"), email, name),
    )
    sync_member(db, user_id, profile, name or username)
    return user_id


def sync_member(db, user_id: str, profile: dict, username: str) -> None:
    """Public display name for events this account shares (email stays private)."""
    name = clean((profile or {}).get("name"), 60) or username
    email = clean((profile or {}).get("email"), 120)
    db.execute(
        "INSERT INTO members (user_id, name, email, updated_at) VALUES (?, ?, ?, ?) "
        "ON CONFLICT(user_id) DO UPDATE SET name = excluded.name, email = excluded.email, updated_at = excluded.updated_at",
        (user_id, name, email, datetime.now().isoformat(timespec="seconds")),
    )
    db.execute("UPDATE events SET host = ? WHERE created_by = ? AND host = 'A Bloom neighbor'", (name, user_id))


def account_json(row) -> dict:
    return {
        "id": row["user_id"],
        "username": row["username"],
        "email": row["email"],
        "name": row["name"],
        "profile": json.loads(row["profile_json"] or "{}"),
        "saved": json.loads(row["saved_json"] or "[]"),
    }


def clean_profile(value) -> dict:
    if not isinstance(value, dict):
        return {}
    text = lambda k, n: clean(value.get(k), n)
    words = lambda k: [clean(v, 30) for v in (value.get(k) or [])[:20] if isinstance(v, str)]
    email = text("email", 120)
    return {
        "name": text("name", 60), "email": email if EMAIL_RE.match(email) else "",
        "interests": words("interests"), "area": text("area", 20), "distance": text("distance", 20),
        "transport": words("transport"), "days": words("days"), "times": words("times"),
        "group": text("group", 20), "needs": words("needs"), "notes": text("notes", 500),
        "completed": bool(value.get("completed")),
        "reminderEmail": text("reminderEmail", 120) if EMAIL_RE.match(text("reminderEmail", 120)) else "",
        "phone": re.sub(r"[^0-9+]", "", text("phone", 30))[:16],
        "reminderTiming": text("reminderTiming", 4) if text("reminderTiming", 4) in ("1d", "2h") else "1d",
        "language": text("language", 5) if text("language", 5) in ("en", "es") else "en",
    }


def clean_saved(value) -> list:
    return [clean(v, 40) for v in (value or [])[:500] if isinstance(v, (str, int))] if isinstance(value, list) else []


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

    def session_user(self, db):
        auth = self.headers.get("Authorization") or ""
        token = auth[7:].strip() if auth.lower().startswith("bearer ") else ""
        if not token:
            return None
        return db.execute(
            "SELECT a.* FROM sessions s JOIN accounts a ON a.user_id = s.user_id WHERE s.token = ?", (token,)
        ).fetchone()

    def new_session(self, db, account) -> None:
        token = secrets.token_urlsafe(32)
        db.execute("INSERT INTO sessions (token, user_id, created_at) VALUES (?, ?, ?)",
                   (token, account["user_id"], datetime.now().isoformat(timespec="seconds")))
        self.send(200, {"token": token, "user": account_json(account)})

    def do_GET(self) -> None:
        path = urlparse(self.path).path.rstrip("/")
        if path == "/api/health":
            return self.send(200, {"ok": True})
        if path == "/api/me":
            with connect() as db:
                account = self.session_user(db)
            return self.send(200, {"user": account_json(account)}) if account else self.send(401, {"error": "Please log in."})
        query = parse_qs(urlparse(self.path).query)
        owner = clean((query.get("owner") or [""])[0], 80)
        if path == "/api/saved":
            with connect() as db:
                if not self.owner_ok(db, owner):
                    return self.send(403, {"error": "Not allowed."})
                ids = [r[0] for r in db.execute("SELECT event_id FROM rsvps WHERE user_id = ? ORDER BY created_at", (owner,))]
            return self.send(200, {"saved": ids})
        if path == "/api/community":
            return self.list_posts(owner)
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
        if path == "/api/saved":
            with connect() as db:
                owner = clean(body.get("owner"), 80)
                if not self.owner_ok(db, owner):
                    return self.send(403, {"error": "Not allowed."})
                try:
                    event_id = int(body.get("event_id"))
                except (TypeError, ValueError):
                    return self.send(400, {"error": "Missing event."})
                if not db.execute("SELECT 1 FROM events WHERE id = ?", (event_id,)).fetchone():
                    return self.send(404, {"error": "That event is no longer listed."})
                db.execute("INSERT OR IGNORE INTO rsvps (user_id, event_id) VALUES (?, ?)", (owner, event_id))
            return self.send(200, {"saved": True})
        if path == "/api/saved/merge":
            with connect() as db:
                account = self.session_user(db)
                guest = clean(body.get("from"), 80)
                if not account or not guest.startswith("bloom-"):
                    return self.send(400, {"error": "Nothing to merge."})
                db.execute("INSERT OR IGNORE INTO rsvps (user_id, event_id, created_at) "
                           "SELECT ?, event_id, created_at FROM rsvps WHERE user_id = ?", (account["user_id"], guest))
                db.execute("DELETE FROM rsvps WHERE user_id = ?", (guest,))
                ids = [r[0] for r in db.execute("SELECT event_id FROM rsvps WHERE user_id = ?", (account["user_id"],))]
            return self.send(200, {"saved": ids})
        if path == "/api/community":
            return self.create_post(body)
        join = re.fullmatch(r"/api/community/(\d+)/join", path)
        if join:
            return self.toggle_join(int(join.group(1)), clean(body.get("owner"), 80))
        comment = re.fullmatch(r"/api/community/(\d+)/comments", path)
        if comment:
            return self.add_comment(int(comment.group(1)), body)
        if path == "/api/register":
            return self.register(body)
        if path == "/api/login":
            return self.login(body)
        if path == "/api/logout":
            with connect() as db:
                auth = self.headers.get("Authorization") or ""
                db.execute("DELETE FROM sessions WHERE token = ?", (auth[7:].strip(),))
            return self.send(200, {"ok": True})
        report = re.fullmatch(r"/api/events/(\d+)/report", path)
        if report:
            return self.report_event(int(report.group(1)), clean(body.get("user"), 80))
        if path != "/api/events":
            return self.send(404, {"error": "Not found"})
        with connect() as db:
            account = self.session_user(db)
            if not account:
                return self.send(401, {"error": "Please create a free account or log in to share events, so neighbors know who is hosting."})
            body["user"] = account["user_id"]
            event, problem = validate(body)
            if problem:
                return self.send(400, {"error": problem})
            poster = member(db, account["user_id"])
            if event["host"] == "A Bloom neighbor":
                event["host"] = poster["name"] if poster else account["username"]
            cols = ", ".join(event)
            marks = ", ".join("?" for _ in event)
            cursor = db.execute(f"INSERT INTO events ({cols}) VALUES ({marks})", tuple(event.values()))
            row = db.execute("SELECT * FROM events WHERE id = ?", (cursor.lastrowid,)).fetchone()
        self.send(201, {"event": to_json(row)})

    def owner_ok(self, db, owner: str) -> bool:
        """Guests act under their own random "bloom-…" id; account ids need that account's session."""
        if owner.startswith("acct-"):
            account = self.session_user(db)
            return bool(account and account["user_id"] == owner)
        return owner.startswith("bloom-") and 10 <= len(owner) <= 80

    # ---- community feed -------------------------------------------------
    def list_posts(self, owner: str) -> None:
        with connect() as db:
            posts = [dict(r) for r in db.execute(
                "SELECT p.*, COALESCE(m.name, 'A Bloom neighbor') AS poster_name, "
                "  (SELECT COUNT(*) FROM post_joins j WHERE j.post_id = p.id) AS joins, "
                "  EXISTS(SELECT 1 FROM post_joins j WHERE j.post_id = p.id AND j.owner = ?) AS joined "
                "FROM posts p LEFT JOIN members m ON m.user_id = p.user_id ORDER BY p.created_at DESC LIMIT 200",
                (owner,),
            )]
            comments = {}
            for c in db.execute(
                "SELECT c.*, COALESCE(m.name, 'A Bloom neighbor') AS name FROM post_comments c "
                "LEFT JOIN members m ON m.user_id = c.user_id ORDER BY c.created_at"
            ):
                comments.setdefault(c["post_id"], []).append({
                    "id": c["id"], "name": c["name"], "body": c["body"], "createdAt": c["created_at"],
                    "mine": c["user_id"] == owner,
                })
        self.send(200, {"posts": [{
            "id": p["id"], "category": p["category"], "title": p["title"], "body": p["body"],
            "schedule": p["schedule"], "place": p["place"], "createdAt": p["created_at"],
            "posterName": p["poster_name"], "mine": p["user_id"] == owner, "sample": bool(p["is_sample"]),
            "joins": p["joins"], "joined": bool(p["joined"]), "comments": comments.get(p["id"], []),
        } for p in posts]})

    def create_post(self, body: dict) -> None:
        with connect() as db:
            account = self.session_user(db)
            if not account:
                return self.send(401, {"error": "Please create a free account or log in to start a group, so neighbors know who is organizing it."})
            title = clean(body.get("title"), 100)
            category = clean(body.get("category"), 20)
            if not title:
                return self.send(400, {"error": "Please give your group or meetup a name."})
            if category not in COMMUNITY_CATEGORIES:
                category = "other"
            cursor = db.execute(
                "INSERT INTO posts (user_id, category, title, body, schedule, place, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (account["user_id"], category, title, clean(body.get("body"), 1000), clean(body.get("schedule"), 120),
                 clean(body.get("place"), 140), now_iso()),
            )
        self.send(201, {"id": cursor.lastrowid})

    def toggle_join(self, post_id: int, owner: str) -> None:
        with connect() as db:
            if not self.owner_ok(db, owner):
                return self.send(403, {"error": "Not allowed."})
            if not db.execute("SELECT 1 FROM posts WHERE id = ?", (post_id,)).fetchone():
                return self.send(404, {"error": "That group was removed."})
            if db.execute("DELETE FROM post_joins WHERE post_id = ? AND owner = ?", (post_id, owner)).rowcount:
                joined = False
            else:
                db.execute("INSERT INTO post_joins (post_id, owner, created_at) VALUES (?, ?, ?)", (post_id, owner, now_iso()))
                joined = True
            joins = db.execute("SELECT COUNT(*) FROM post_joins WHERE post_id = ?", (post_id,)).fetchone()[0]
        self.send(200, {"joined": joined, "joins": joins})

    def add_comment(self, post_id: int, body: dict) -> None:
        with connect() as db:
            account = self.session_user(db)
            if not account:
                return self.send(401, {"error": "Please create a free account or log in to comment."})
            text = clean(body.get("body"), 600)
            if not text:
                return self.send(400, {"error": "Please write a comment first."})
            if not db.execute("SELECT 1 FROM posts WHERE id = ?", (post_id,)).fetchone():
                return self.send(404, {"error": "That group was removed."})
            db.execute("INSERT INTO post_comments (post_id, user_id, body, created_at) VALUES (?, ?, ?, ?)",
                       (post_id, account["user_id"], text, now_iso()))
        self.send(201, {"ok": True})

    def register(self, body: dict) -> None:
        email = str(body.get("email") or "").strip().lower()
        name = clean(body.get("name"), 60)
        password = str(body.get("password") or "")
        if not EMAIL_RE.match(email) or len(email) > 120:
            return self.send(400, {"error": "That email doesn’t look quite right. Please check it."})
        if not name:
            return self.send(400, {"error": "Please tell us what to call you."})
        if len(password) < 6:
            return self.send(400, {"error": "Please choose a password with at least 6 characters."})
        if len(password) > 200:
            return self.send(400, {"error": "That password is too long."})
        with connect() as db:
            if db.execute("SELECT 1 FROM accounts WHERE email = ? OR username = ?", (email, email)).fetchone():
                return self.send(409, {"error": "There’s already an account with that email. Try logging in instead."})
            profile = clean_profile(body.get("profile"))
            profile["name"] = profile.get("name") or name
            if not profile.get("email"):
                profile["email"] = email
            user_id = create_account(db, email, password, profile, [], email=email, name=name)
            account = db.execute("SELECT * FROM accounts WHERE user_id = ?", (user_id,)).fetchone()
            self.new_session(db, account)

    def login(self, body: dict) -> None:
        email = str(body.get("email") or body.get("username") or "").strip()
        password = str(body.get("password") or "")
        with connect() as db:
            account = db.execute("SELECT * FROM accounts WHERE email = ? COLLATE NOCASE OR username = ?", (email, email)).fetchone()
            if not account or not hmac.compare_digest(hash_password(password, account["salt"]), account["password_hash"]):
                return self.send(401, {"error": "That email and password don’t match. Please try again."})
            self.new_session(db, account)

    def do_PUT(self) -> None:
        if urlparse(self.path).path.rstrip("/") != "/api/me":
            return self.send(404, {"error": "Not found"})
        body = self.read_json()
        if body is None:
            return self.send(400, {"error": "Something went wrong reading that. Please try again."})
        with connect() as db:
            account = self.session_user(db)
            if not account:
                return self.send(401, {"error": "Please log in."})
            if "profile" in body:
                profile = clean_profile(body.get("profile"))
                db.execute("UPDATE accounts SET profile_json = ? WHERE user_id = ?", (json.dumps(profile), account["user_id"]))
                sync_member(db, account["user_id"], profile, account["name"] or account["username"])
                if profile.get("name"):
                    db.execute("UPDATE accounts SET name = ? WHERE user_id = ?", (profile["name"], account["user_id"]))
            if "saved" in body:
                db.execute("UPDATE accounts SET saved_json = ? WHERE user_id = ?",
                           (json.dumps(clean_saved(body.get("saved"))), account["user_id"]))
            account = db.execute("SELECT * FROM accounts WHERE user_id = ?", (account["user_id"],)).fetchone()
        self.send(200, {"user": account_json(account)})

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
        path = parsed.path.rstrip("/")
        saved = re.fullmatch(r"/api/saved/(\d+)", path)
        if saved:
            owner = clean((parse_qs(parsed.query).get("owner") or [""])[0], 80)
            with connect() as db:
                if not self.owner_ok(db, owner):
                    return self.send(403, {"error": "Not allowed."})
                db.execute("DELETE FROM rsvps WHERE user_id = ? AND event_id = ?", (owner, int(saved.group(1))))
            return self.send(200, {"saved": False})
        post = re.fullmatch(r"/api/community/(\d+)", path)
        if post:
            with connect() as db:
                account = self.session_user(db)
                if not account:
                    return self.send(401, {"error": "Please log in."})
                removed = db.execute("DELETE FROM posts WHERE id = ? AND user_id = ?", (int(post.group(1)), account["user_id"])).rowcount
                if removed:
                    db.execute("DELETE FROM post_joins WHERE post_id = ?", (int(post.group(1)),))
                    db.execute("DELETE FROM post_comments WHERE post_id = ?", (int(post.group(1)),))
            return self.send(200 if removed else 403, {"deleted": bool(removed)})
        match = re.fullmatch(r"/api/events/(\d+)", path)
        if not match:
            return self.send(404, {"error": "Not found"})
        with connect() as db:
            account = self.session_user(db)
            if not account:
                return self.send(401, {"error": "Please log in."})
            user = account["user_id"]
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
