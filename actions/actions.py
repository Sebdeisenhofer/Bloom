import os
import re
import sqlite3
from datetime import date
from pathlib import Path
from typing import Any

from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher

from actions.i18n import friendly_date_in, language_of, t


DB_PATH = os.environ.get("COMMUNITY_DB_PATH", "/data/community.sqlite3")


def connect() -> sqlite3.Connection:
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH, timeout=10)
    db.row_factory = sqlite3.Row
    return db


def initialize_database() -> None:
    with connect() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS profiles (
                user_id TEXT PRIMARY KEY,
                hobbies TEXT NOT NULL DEFAULT '',
                partner_activities TEXT NOT NULL DEFAULT '',
                interests TEXT NOT NULL DEFAULT '',
                preferred_times TEXT NOT NULL DEFAULT '',
                preferred_group_size TEXT NOT NULL DEFAULT '',
                travel_distance TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                location TEXT NOT NULL,
                category TEXT NOT NULL,
                tags TEXT NOT NULL,
                group_size TEXT NOT NULL,
                description TEXT NOT NULL,
                host TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY,
                owner TEXT NOT NULL,
                event_id INTEGER NOT NULL,
                timing TEXT NOT NULL,
                channel TEXT NOT NULL,
                contact TEXT NOT NULL DEFAULT '',
                send_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                detail TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                sent_at TEXT,
                lang TEXT NOT NULL DEFAULT 'en',
                UNIQUE (owner, event_id, timing, channel)
            );
            CREATE TABLE IF NOT EXISTS rsvps (
                user_id TEXT NOT NULL,
                event_id INTEGER NOT NULL REFERENCES events(id),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, event_id)
            );
            """
        )
        # Columns used by community-posted events (website + chat). Added in place for older databases.
        existing = {row["name"] for row in db.execute("PRAGMA table_info(events)")}
        for name, ddl in (
            ("area", "TEXT NOT NULL DEFAULT ''"),
            ("cost", "TEXT NOT NULL DEFAULT ''"),
            ("needs", "TEXT NOT NULL DEFAULT ''"),
            ("created_by", "TEXT"),
            ("created_at", "TEXT"),
            # '' = built-in sample, 'community' = posted by a neighbor, otherwise a real feed (e.g. 'library').
            ("source", "TEXT NOT NULL DEFAULT ''"),
            ("external_id", "TEXT"),
            ("url", "TEXT NOT NULL DEFAULT ''"),
            ("end_time", "TEXT NOT NULL DEFAULT ''"),
            # Where the listing came from, and where to buy tickets (Phase 2)
            ("source_url", "TEXT NOT NULL DEFAULT ''"),
            ("ticket_url", "TEXT NOT NULL DEFAULT ''"),
            ("is_sample", "INTEGER NOT NULL DEFAULT 0"),
            # Location for distance search anywhere in the US (Phase 3)
            ("lat", "REAL"),
            ("lon", "REAL"),
            ("city", "TEXT NOT NULL DEFAULT ''"),
        ):
            if name not in existing:
                db.execute(f"ALTER TABLE events ADD COLUMN {name} {ddl}")
        db.execute("CREATE UNIQUE INDEX IF NOT EXISTS events_external_id ON events(external_id)")
        if "lang" not in {row["name"] for row in db.execute("PRAGMA table_info(reminders)")}:
            db.execute("ALTER TABLE reminders ADD COLUMN lang TEXT NOT NULL DEFAULT 'en'")
        # The original invented demo events (no source) are retired in favor of real and sample listings.
        db.execute("DELETE FROM events WHERE source = '' AND created_by IS NULL")
        db.execute("UPDATE events SET source_url = url WHERE source_url = '' AND url != ''")
        # First start (or no internet yet): put the labelled sample listings in place right away.
        if db.execute("SELECT COUNT(*) FROM events WHERE source != 'community'").fetchone()[0] == 0:
            from actions.sources import sample_rows
            for row in sample_rows():
                cols = ", ".join(row)
                db.execute(f"INSERT OR IGNORE INTO events ({cols}) VALUES ({', '.join('?' for _ in row)})", tuple(row.values()))


def profile_for(user_id: str) -> dict[str, str] | None:
    initialize_database()
    with connect() as db:
        row = db.execute("SELECT * FROM profiles WHERE user_id = ?", (user_id,)).fetchone()
    return dict(row) if row else None


def tracker_user(tracker: Tracker) -> str:
    return str(tracker.get_slot("user_id") or tracker.sender_id or "sample-salem-user")


def save_profile(tracker: Tracker, updates: dict[str, Any]) -> dict[str, str]:
    user_id = tracker_user(tracker)
    current = profile_for(user_id) or {}
    values = {
        key: str(updates.get(key) if updates.get(key) is not None else current.get(key, ""))
        for key in (
            "hobbies",
            "partner_activities",
            "interests",
            "preferred_times",
            "preferred_group_size",
            "travel_distance",
        )
    }
    with connect() as db:
        db.execute(
            """INSERT INTO profiles
            (user_id, hobbies, partner_activities, interests, preferred_times, preferred_group_size, travel_distance)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
              hobbies=excluded.hobbies, partner_activities=excluded.partner_activities,
              interests=excluded.interests, preferred_times=excluded.preferred_times,
              preferred_group_size=excluded.preferred_group_size, travel_distance=excluded.travel_distance,
              updated_at=CURRENT_TIMESTAMP""",
            (user_id, *(values[k] for k in values)),
        )
    return values


def words(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def extract_filters(text: str) -> dict[str, str]:
    t = text.lower()
    filters: dict[str, str] = {}
    for day in ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"):
        if day in t:
            filters["day"] = day
    if "morning" in t:
        filters["time"] = "morning"
    elif "afternoon" in t:
        filters["time"] = "afternoon"
    elif "evening" in t or "night" in t:
        filters["time"] = "evening"
    for place in ("keizer", "west salem", "south salem", "downtown", "riverfront", "minto-brown"):
        if place in t:
            filters["location"] = place
    for category in ("book", "garden", "walking", "craft", "dance", "yoga", "bird", "art", "music", "food", "history"):
        if category in t:
            filters["category"] = category
    return filters


def current_events(db: sqlite3.Connection) -> list[dict[str, Any]]:
    """Upcoming events people can actually attend (real feeds, labelled samples, neighbors' posts)."""
    rows = db.execute("SELECT * FROM events WHERE date >= ? ORDER BY date, time", (date.today().isoformat(),))
    return [dict(row) for row in rows]


# ---------------------------------------------------------------------------
# Understanding dates and times people type or say ("next Tuesday", "2pm")
# ---------------------------------------------------------------------------
WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}
NUMBER_WORDS = {w: i for i, w in enumerate(
    ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve"])}


def parse_event_date(text: str, today: date | None = None) -> date | None:
    from datetime import timedelta

    today = today or date.today()
    t = str(text or "").lower().strip()
    t = re.sub(r"(\d+)(st|nd|rd|th)\b", r"\1", t)
    if not t:
        return None
    if "today" in t or "tonight" in t:
        return today
    if "day after tomorrow" in t:
        return today + timedelta(days=2)
    if "tomorrow" in t:
        return today + timedelta(days=1)
    m = re.search(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b", t)
    if m:
        try:
            return date(int(m[1]), int(m[2]), int(m[3]))
        except ValueError:
            return None
    m = re.search(r"\b(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?\b", t)
    if m:
        year = int(m[3]) if m[3] else today.year
        year = year + 2000 if year < 100 else year
        try:
            d = date(year, int(m[1]), int(m[2]))
        except ValueError:
            return None
        return d.replace(year=d.year + 1) if not m[3] and d < today else d
    m = re.search(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+(\d{1,2})\b", t) or \
        re.search(r"\b(\d{1,2})\s+(?:of\s+)?(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\b", t)
    if m:
        month_word, day_num = (m[1], m[2]) if m[1].isalpha() else (m[2], m[1])
        try:
            d = date(today.year, MONTHS[month_word[:3]], int(day_num))
        except ValueError:
            return None
        return d.replace(year=d.year + 1) if d < today else d
    for i, name in enumerate(WEEKDAYS):
        if name in t or re.search(rf"\b{name[:3]}\b", t):
            if "next week" in t:  # that weekday in the following Monday–Sunday week
                return today + timedelta(days=7 - today.weekday() + i)
            ahead = (i - today.weekday()) % 7  # the coming one ("Friday" said on a Friday = today)
            if "next" in t and ahead == 0:
                ahead = 7
            return today + timedelta(days=ahead)
    m = re.search(r"\bin (\d+|a|one|two|three) (day|week)s?\b", t)
    if m:
        n = 1 if m[1] in ("a", "one") else NUMBER_WORDS.get(m[1]) or int(m[1])
        return today + timedelta(days=n * (7 if m[2] == "week" else 1))
    return None


def parse_event_time(text: str) -> str | None:
    """Return a time like '2:30 PM', or None if it can't be understood."""
    t = str(text or "").lower().strip().replace(".", "")
    if not t:
        return None
    if "noon" in t or "midday" in t:
        return "12:00 PM"
    for word, num in NUMBER_WORDS.items():
        t = re.sub(rf"\b{word}\b", str(num), t)
    m = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm|a m|p m|in the morning|in the afternoon|in the evening|at night|o'?clock)?\b", t)
    if not m:
        return None
    hour, minute, suffix = int(m[1]), int(m[2] or 0), (m[3] or "").replace(" ", "")
    if minute > 59 or hour > 23:
        return None
    if "half past" in t:
        minute = 30
    elif "quarter past" in t:
        minute = 15
    if suffix in ("pm", "intheafternoon", "intheevening", "atnight") and hour < 12:
        hour += 12
    elif suffix in ("am", "inthemorning") and hour == 12:
        hour = 0
    elif not suffix and 1 <= hour <= 6:
        hour += 12  # "3" for a community event almost always means 3 PM
    if not 0 <= hour <= 23:
        return None
    return f"{(hour + 11) % 12 + 1}:{minute:02d} {'AM' if hour < 12 else 'PM'}"


INTEREST_KEYWORDS = {
    "gardening": ("garden", "plant", "seed", "flower", "compost", "jardín", "jardin", "jardinería", "jardineria", "plantas", "flores", "huerto"),
    "music": ("music", "concert", "sing", "choir", "band", "jazz", "ukulele", "symphony", "orchestra", "musician", "música", "musica", "concierto", "coro", "canto", "orquesta"),
    "crafts": ("craft", "knit", "knitting", "crochet", "quilt", "sew", "paint", "art", "artist", "pottery", "draw", "journal", "journaling", "manualidades", "arte", "pintura", "tejer", "tejido", "acuarela", "artesanía"),
    "books": ("book", "read", "reader", "author", "poetry", "poem", "writing", "writer", "novel", "libro", "lectura", "leer", "club de lectura", "poesía", "escritura"),
    "walking": ("walk", "hike", "hiking", "nature", "bird", "birding", "trail", "park", "caminar", "caminata", "paseo", "naturaleza", "parque", "aves", "sendero"),
    "fitness": ("yoga", "tai chi", "exercise", "fitness", "stretch", "zumba", "balance", "pilates", "ejercicio", "yoga", "estiramiento", "taichí", "tai chi", "baile suave"),
    "games": ("game", "bingo", "chess", "card", "bridge", "puzzle", "trivia", "mahjong", "cribbage", "lego", "juegos", "juego", "cartas", "bingo", "ajedrez", "rompecabezas", "trivia"),
    "cooking": ("cook", "potluck", "baking", "recipe", "food", "lunch", "dinner", "tea", "cocina", "cocinar", "comida", "almuerzo", "cena", "té"),
    "faith": ("church", "faith", "prayer", "worship", "bible", "spiritual", "iglesia", "fe", "oración", "espiritual"),
    "volunteering": ("volunteer", "volunteering", "work party", "voluntario", "voluntaria", "voluntariado", "voluntarios"),
    "learning": ("class", "workshop", "learn", "lecture", "presentation", "esl", "seminar", "course", "citizenship", "tutor", "clase", "taller", "aprender", "charla", "conferencia", "curso"),
    "tech": ("tech", "technology", "computer", "phone", "smartphone", "tablet", "digital", "internet", "email", "laptop", "ipad", "tecnología", "teléfono", "celular", "computadora", "tableta", "internet"),
    "history": ("history", "historical", "museum", "heritage", "genealogy", "ancestry", "historia", "museo", "patrimonio", "genealogía"),
    "dancing": ("dance", "dancing", "ballroom", "swing", "baile", "bailar", "danza"),
    "health": ("health", "medicare", "wellness", "memory", "nutrition", "blood pressure", "caregiver", "dementia", "salud", "bienestar", "medicare", "memoria", "nutrición"),
    "sports": ("football", "basketball", "volleyball", "soccer", "baseball", "softball", "swim", "swimming",
               "bearcats", "athletics", "tennis", "deporte", "deportes", "fútbol", "baloncesto", "básquetbol", "voleibol", "partido"),
    "movies": ("movie", "film", "theater", "theatre", "play", "comedy", "cinema", "película", "cine", "teatro", "comedia"),
    "family": ("kid", "child", "children", "storytime", "toddler", "preschool", "teen", "family", "families",
               "grandparent", "baby", "babies", "infant", "tween"),
    "social": ("coffee", "social", "conversation", "friendship", "club", "chat", "discussion", "gathering", "neighbor", "café", "charlar", "amigos", "vecinos", "reunión"),
    "language": ("french", "spanish conversation", "german", "italian", "japanese", "esl", "conversation group",
                 "conversation circle", "language exchange", "language group", "language club",
                 "español", "francés", "idioma", "idiomas", "conversación", "círculo de conversación", "cercle", "français"),
}
_INTEREST_PATTERNS = {
    key: re.compile(r"\b(?:" + "|".join(re.escape(w) for w in words) + r")(?:s|es|ing|ers?)?\b", re.I)
    for key, words in INTEREST_KEYWORDS.items()
}


def infer_interest_tags(*texts: str) -> list[str]:
    blob = " ".join(str(t or "") for t in texts)
    return [key for key, pattern in _INTEREST_PATTERNS.items() if pattern.search(blob)]


def infer_area(location: str) -> str:
    loc = str(location or "").lower()
    for area, words in (
        ("west", ("west salem", "wallace", "edgewater")),
        ("keizer", ("keizer",)),
        ("south", ("south salem", "commercial st se", "liberty rd s", "minto", "bush", "fairmount")),
        ("northeast", ("portland rd", "lancaster", "silverton rd", "northeast", " ne")),
        ("east", ("state st", "southeast", " se", "east salem")),
        ("downtown", ("downtown", "main library", "liberty st", "riverfront", "court st", "state capitol")),
    ):
        if any(w in loc for w in words):
            return area
    return ""


# ---------------------------------------------------------------------------
# Yes / no and "skip" answers
# ---------------------------------------------------------------------------
YES_WORDS = ("yes", "yeah", "yea", "yep", "yup", "sure", "ok", "okay", "correct", "right", "true",
             "sí", "si", "claro", "vale", "de acuerdo", "publícalo", "publicalo", "correcto",
             "confirm", "confirmed", "post", "please", "absolutely", "definitely", "of course", "sounds good",
             "looks good", "that's right", "thats right", "go ahead", "do it", "y")
NO_WORDS = ("no", "nope", "nah", "not", "don't", "dont", "cancel", "stop", "false", "wrong", "wait", "n",
            "cancelar", "todavía no", "aún no",
            "never mind", "nevermind", "hold on")
SKIP_WORDS = ("skip", "no", "none", "nope", "nothing", "n/a", "na", "no thanks", "no thank you", "pass",
              "omitir", "saltar", "nada", "ninguno", "ninguna", "no gracias",
              "not really", "leave it blank", "blank", "-", "no description")
NO_DESCRIPTION = ""  # stored when the optional description is skipped


def parse_yes_no(text: Any) -> bool | None:
    """True for yes-like answers, False for no-like answers, None if unclear.

    Handles real booleans and the "True"/"False" strings the LLM command generator writes.
    "No" wins over "yes" ("yes, but no" / "not yet") so an event is never posted by mistake.
    """
    if isinstance(text, bool):
        return text
    t = re.sub(r"[^a-záéíóúñü' /]", " ", str(text or "").lower().replace("’", "'"))
    t = re.sub(r"\s+", " ", t).strip()
    if not t:
        return None
    padded = f" {t} "
    if any(f" {w} " in padded for w in NO_WORDS):
        return False
    if any(f" {w} " in padded for w in YES_WORDS):
        return True
    return None


def is_skip(text: Any) -> bool:
    t = re.sub(r"[^a-záéíóúñü/ -]", " ", str(text or "").lower()).strip()
    t = re.sub(r"\s+", " ", t)
    return t in SKIP_WORDS or t.startswith(("skip", "no description", "nothing to add", "none", "omitir", "sin descripci"))


def friendly_date(iso: str) -> str:
    try:
        return date.fromisoformat(iso).strftime("%A, %B %-d")
    except (ValueError, TypeError):
        return str(iso)


def event_time_period(value: str) -> str:
    parts = value.lower().split()
    if not parts or not re.match(r"^\d{1,2}(:\d{2})?$", parts[0]):
        return "afternoon"
    hour = int(parts[0].split(":")[0])
    suffix = parts[-1] if len(parts) > 1 else ""
    if suffix == "am" and hour != 12:
        return "morning"
    if suffix == "pm" and hour != 12 and hour >= 5:
        return "evening"
    return "afternoon"


QUERY_STOPWORDS = set("""find show events event near me please want like tell about what whats what's is are on
this week weekend today tomorrow the a an any some for in at to of and or with my i you can do there anything
happening going something things activities activity""".split())


def tag_keys(*texts: str) -> set[str]:
    """Interest keys ("gardening", "music", ...) from comma-separated tags or free text."""
    keys = set()
    for text in texts:
        for part in str(text or "").split(","):
            part = part.strip().lower()
            if part in INTEREST_KEYWORDS:
                keys.add(part)
        keys.update(infer_interest_tags(text))
    return keys


def rank_events(profile: dict[str, Any], query: str = "", location: dict | None = None) -> list[dict[str, Any]]:
    """Order every upcoming event by fit. Nothing is dropped: relevance only changes the order."""
    from actions.sources import source_info

    interest_keys = tag_keys(*(str(profile.get(k, "")) for k in ("hobbies", "interests", "partner_activities")))
    interest_keys |= set(profile.get("interest_keys") or [])
    query_keys = tag_keys(query)
    filters = extract_filters(query)
    query_words = words(query) - QUERY_STOPWORDS - set(words(" ".join(filters.values())))
    query_words -= set(WEEKDAYS) | {"morning", "afternoon", "evening", "tonight"}
    with connect() as db:
        rows = current_events(db)
    ranked = []
    for event in rows:
        keys = tag_keys(event["tags"], event["category"]) | tag_keys(event["title"], event["description"])
        info = source_info(event.get("source") or "")
        score, reasons = 0, []
        liked = sorted(interest_keys & keys)
        if liked:
            score += 4 * len(liked)
            reasons.append(("why_interest", {"list": ", ".join(liked[:3])}))
        asked = sorted(query_keys & keys)
        if asked:
            score += 6 * len(asked)
            reasons.append(("why_asked", {"list": ", ".join(asked[:3])}))
        title_hits = query_words & words(event["title"] + " " + event.get("host", ""))
        if title_hits:  # naming the event itself is the strongest signal
            score += 4 * len(title_hits)
        if info["weight"]:
            score += info["weight"]
            if event.get("source") == "center50":
                reasons.append(("why_center50", {}))
        if info.get("specialty") and interest_keys & set(info["specialty"]):
            score += 2
            reasons.append(("why_specialty", {"source": info["name"]}))
        pref_time = str(profile.get("preferred_times", "")).lower()
        time_period = event_time_period(event["time"])
        if pref_time and time_period in pref_time:
            score += 2
            reasons.append(("why_time", {"tod": time_period}))
        group_pref = str(profile.get("preferred_group_size", "")).lower()
        if group_pref and event["group_size"] in group_pref:
            score += 1
        if filters.get("time") == time_period:
            score += 3
        if filters.get("location") and filters["location"] in event["location"].lower():
            score += 2
        try:
            event_day = date.fromisoformat(event["date"]).strftime("%A").lower()
        except ValueError:
            event_day = ""
        if filters.get("day") and filters["day"] == event_day:
            score += 3
        event["miles"] = None
        if location and event.get("lat") is not None:
            from actions.geo import distance_to
            event["miles"] = round(distance_to(location, event["lat"], event["lon"]), 1)
        event["score"] = score
        event["reasons"] = reasons
        ranked.append(event)
    if location:
        radius = location.get("radius", 25)
        near = lambda e: e["miles"] is not None and e["miles"] <= radius
        # Nearby first (best fit, nudged by closeness), then everything else by distance. Nothing is dropped.
        return sorted(ranked, key=lambda e: (not near(e), (e["miles"] / 3 - e["score"]) if near(e) else round((e["miles"] or 1e9) / 5) * 100 - e["score"], e["date"]))
    return sorted(ranked, key=lambda event: (-event["score"], event["date"], event["title"]))


def event_card(event: dict[str, Any]) -> dict[str, Any]:
    from actions.sources import source_info

    info = source_info(event.get("source") or "")
    return {
        "id": event["id"],
        "title": event["title"],
        "date": event["date"],
        "time": event["time"],
        "end_time": event.get("end_time") or "",
        "location": event["location"],
        "category": event["category"],
        "description": event["description"][:300],
        "host": event.get("host", ""),
        "source": event.get("source") or "",
        "source_name": info["name"],
        "source_icon": info["icon"],
        "source_url": event.get("source_url") or event.get("url") or "",
        "ticket_url": event.get("ticket_url") or "",
        "sample": bool(event.get("is_sample")),
        "miles": event.get("miles"),
        "score": event.get("score", 0),
    }


# ---------------------------------------------------------------------------
# "Go back" / "previous question": rewind the active flow by one question.
# Rasa CALM keeps its place in a flow on the dialogue stack; a custom action can
# update the stack with a JSON-patch "stack" event (the same event Rasa itself uses).
# ---------------------------------------------------------------------------
GO_BACK_STEPS = {
    # every step id in order, with the slot each collect step fills (None for other steps)
    "create_event": [
        ("ask_title", "event_title"), ("ask_date", "event_date"), ("ask_time", "event_time"),
        ("ask_location", "event_location"), ("ask_host", "event_host"), ("ask_description", "event_description"),
        ("review", None), ("ask_confirmation", "event_confirmation"),
    ],
    "onboarding_survey": [
        ("ask_hobbies", "hobbies"), ("ask_partner_activities", "partner_activities"), ("ask_interests", "interests"),
        ("ask_preferred_times", "preferred_times"), ("ask_preferred_group_size", "preferred_group_size"),
        ("ask_travel_distance", "travel_distance"),
    ],
}


def go_back_plan(stack: list[dict]) -> dict | None:
    """Work out how to return to the previous question. Returns None when there is nothing to go back to."""
    for index in range(len(stack) - 1, -1, -1):
        frame = stack[index]
        steps = GO_BACK_STEPS.get(frame.get("flow_id", ""))
        if frame.get("type") != "flow" or not steps:
            continue
        ids = [step_id for step_id, _ in steps]
        current = frame.get("step_id", "")
        if current not in ids:
            return {"frame": index, "first": True}
        position = ids.index(current)
        previous = [i for i in range(position) if steps[i][1]]
        if not previous:
            return {"frame": index, "first": True, "slot": steps[position][1]}
        target = previous[-1]
        return {
            "frame": index,
            "first": False,
            "restart_after": ids[target - 1] if target > 0 else "START",
            "clear": [slot for _, slot in steps[target:position + 1] if slot],
            "question_slot": steps[target][1],
        }
    return None


# ---------------------------------------------------------------------------
# Who is chatting: Rasa onboarding answers, the website survey (accounts and
# guests send it as message metadata), and the conversation language.
# ---------------------------------------------------------------------------
def web_metadata(tracker: Tracker) -> dict:
    meta = (tracker.latest_message or {}).get("metadata") or {}
    return meta if isinstance(meta, dict) else {}


def account_profile(user_id: str) -> dict:
    """The website profile stored with a signed-in account (acct-…), if any."""
    import json

    if not str(user_id).startswith("acct-"):
        return {}
    try:
        with connect() as db:
            row = db.execute("SELECT profile_json, email FROM accounts WHERE user_id = ?", (user_id,)).fetchone()
    except sqlite3.Error:
        return {}
    if not row:
        return {}
    data = json.loads(row["profile_json"] or "{}")
    data.setdefault("email", row["email"])
    return data


def chat_profile(tracker: Tracker) -> dict:
    user = tracker_user(tracker)
    profile = dict(profile_for(user) or {})
    profile.update({key: tracker.get_slot(key) for key in (
        "hobbies", "interests", "partner_activities", "preferred_times", "preferred_group_size",
    ) if tracker.get_slot(key)})
    web = account_profile(user)
    meta = web_metadata(tracker)
    keys = set(web.get("interests") or []) | set(meta.get("interests") or [])
    if keys:
        profile["interest_keys"] = sorted(k for k in keys if k in INTEREST_KEYWORDS)
    times = web.get("times") or meta.get("times") or []
    if times and not profile.get("preferred_times"):
        profile["preferred_times"] = " ".join(times)
    return profile


def reasons_text(tracker: Tracker, reasons: list) -> str:
    lang = language_of(tracker)
    parts = []
    for key, values in reasons[:2]:
        if "tod" in values:
            values = {**values, "tod": t(lang, "tod_" + values["tod"])}
        parts.append(t(lang, key, **values))
    return "; ".join(parts)


def find_event_in_text(text: str, fallback_id: str | None = None) -> dict | None:
    """An event by id ("event 42") or by name ("save the Gaiety Hollow Garden Tour")."""
    with connect() as db:
        match = re.search(r"\bevent\s*#?\s*(\d+)\b", text, re.I) or re.fullmatch(r"\s*(\d+)\s*", text)
        if match:
            row = db.execute("SELECT * FROM events WHERE id = ?", (int(match.group(1)),)).fetchone()
            if row:
                return dict(row)
        said = words(text) - QUERY_STOPWORDS - {"save", "go", "rsvp", "remind", "reminder", "add", "guardar", "guarda",
                                                "evento", "sobre", "cuéntame", "yes", "sí", "si", "like", "to", "would", "id"}
        best, best_hits = None, 0
        if said:
            for event in current_events(db):
                hits = len(said & words(event["title"]))
                if hits > best_hits or (hits == best_hits and best and event["date"] < best["date"]):
                    best, best_hits = event, hits
        if best and best_hits >= max(1, min(2, len(said))):
            return best
        if fallback_id:
            row = db.execute("SELECT * FROM events WHERE id = ?", (fallback_id,)).fetchone()
            return dict(row) if row else None
    return None


class ActionLoadProfile(Action):
    def name(self) -> str:
        return "action_load_profile"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: dict) -> list:
        initialize_database()
        user_id = tracker.sender_id or "sample-salem-user"
        profile = profile_for(user_id)
        # Website visitors already answered the survey on the page; don't ask again in chat.
        known = bool(profile) or bool(account_profile(user_id)) or str(user_id).startswith(("bloom-", "acct-"))
        dispatcher.utter_message(text=t(tracker, "welcome_back" if known else "first_hello"))
        events = [SlotSet("user_id", user_id), SlotSet("profile_exists", known)]
        if profile:
            events += [SlotSet(key, profile[key]) for key in (
                "hobbies", "partner_activities", "interests", "preferred_times",
                "preferred_group_size", "travel_distance",
            )]
        return events


class ActionSaveProfile(Action):
    def name(self) -> str:
        return "action_save_profile"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: dict) -> list:
        values = save_profile(tracker, {key: tracker.get_slot(key) for key in (
            "hobbies", "partner_activities", "interests", "preferred_times",
            "preferred_group_size", "travel_distance",
        )})
        dispatcher.utter_message(text=t(tracker, "prefs_saved"))
        return [SlotSet(key, value) for key, value in values.items()] + [SlotSet("profile_exists", True)]


def is_web_guest(sender_id: str | None) -> bool:
    """The website gives guests ids starting with "bloom-"; signed-in accounts use "acct-"."""
    return str(sender_id or "").startswith("bloom-")


class ActionSaveEvent(Action):
    def name(self) -> str:
        return "action_save_event"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: dict) -> list:
        try:
            initialize_database()
        except sqlite3.Error as error:
            print(f"action_save_event: database unavailable: {error}", flush=True)
            dispatcher.utter_message(text=t(tracker, "save_failed"))
            return []
        # The flow only reaches this action after a confirmed "yes" (see create_event in flows.yml);
        # this check is a second safety net so nothing is posted without a clear yes.
        if parse_yes_no(tracker.get_slot("event_confirmation")) is not True:
            dispatcher.utter_message(text=t(tracker, "not_posted"))
            return []
        if is_web_guest(tracker.sender_id):
            dispatcher.utter_message(text=t(tracker, "guest_cannot_post"))
            return []
        fields = [tracker.get_slot(key) for key in ("event_title", "event_date", "event_time", "event_location", "event_host")]
        if not all(fields):
            dispatcher.utter_message(text=t(tracker, "missing_detail"))
            return []
        title, raw_date, raw_time, location, host = (str(f).strip() for f in fields)
        description = str(tracker.get_slot("event_description") or "").strip()
        if is_skip(description):
            description = NO_DESCRIPTION
        day = parse_event_date(raw_date)
        start = parse_event_time(raw_time)
        if not day or day < date.today() or not start:
            dispatcher.utter_message(text=t(tracker, "bad_datetime"))
            return []
        tags = infer_interest_tags(title, description) or ["social"]
        from actions.sources import SALEM, locate

        where = locate(location) or (*SALEM, infer_area(location), "Salem")
        try:
            with connect() as db:  # commits on success
                cursor = db.execute(
                    """INSERT INTO events (title, date, time, location, category, tags, group_size, description, host,
                                           area, cost, needs, created_by, created_at, source, lat, lon, city)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, 'community', ?, ?, ?)""",
                    (title, day.isoformat(), start, location, "Community", ", ".join(tags), "small",
                     description or f"A community event hosted by {host}.", host,
                     where[2] or infer_area(location), "Free", "", tracker_user(tracker), where[0], where[1], where[3]),
                )
                saved = db.execute("SELECT id FROM events WHERE id = ?", (cursor.lastrowid,)).fetchone()
            if not saved:
                raise sqlite3.DatabaseError("event row missing after insert")
        except sqlite3.Error as error:
            print(f"action_save_event: could not save event: {error}", flush=True)
            dispatcher.utter_message(text=t(tracker, "save_failed"))
            return []
        dispatcher.utter_message(
            text=t(tracker, "posted", title=title, date=friendly_date_in(day.isoformat(), language_of(tracker)), time=start),
            json_message={"event_created": {"id": cursor.lastrowid, "title": title}},
        )
        return []


class ValidateEventDate(Action):
    """Runs after the assistant collects event_date; turns "next Tuesday" into a real date."""

    def name(self) -> str:
        return "validate_event_date"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: dict) -> list:
        raw = tracker.get_slot("event_date")
        if raw is None:
            return []
        day = parse_event_date(str(raw))
        if not day:
            dispatcher.utter_message(text=t(tracker, "date_unclear"))
            return [SlotSet("event_date", None)]
        if day < date.today():
            dispatcher.utter_message(text=t(tracker, "date_past"))
            return [SlotSet("event_date", None)]
        return [SlotSet("event_date", day.isoformat())]


class ValidateEventConfirmation(Action):
    """Runs after the "post it?" question. Reads the person's own words, not just the LLM's guess."""

    def name(self) -> str:
        return "validate_event_confirmation"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: dict) -> list:
        if tracker.get_slot("event_confirmation") is None:
            return []  # not answered yet: let the flow ask the question
        said = tracker.latest_message.get("text") or ""
        if said.startswith("/SetSlots"):  # a Yes/No button was pressed: trust its value
            said = ""
        answer = parse_yes_no(said)
        if answer is None:
            answer = parse_yes_no(tracker.get_slot("event_confirmation"))
        if answer is None:
            dispatcher.utter_message(text=t(tracker, "confirm_unclear"))
            return [SlotSet("event_confirmation", None)]
        # Normalized to exactly "yes"/"no" so the flow's branch condition is unambiguous.
        return [SlotSet("event_confirmation", "yes" if answer else "no")]


class ValidateEventDescription(Action):
    """The description is optional: "skip", "no" or "none" leaves it blank."""

    def name(self) -> str:
        return "validate_event_description"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: dict) -> list:
        value = tracker.get_slot("event_description")
        if value is None:
            return []  # not answered yet
        said = tracker.latest_message.get("text") or ""
        if is_skip(said) or is_skip(value):
            return [SlotSet("event_description", "skip")]
        return []


class ActionGoBack(Action):
    def name(self) -> str:
        return "action_go_back"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: dict) -> list:
        import json

        stack = list(getattr(tracker, "stack", None) or [])
        plan = go_back_plan(stack)
        if not plan:
            dispatcher.utter_message(text=t(tracker, "go_back_nothing"))
            return []
        if plan["first"]:
            dispatcher.utter_message(text=t(tracker, "go_back_first"))
            return []
        frame = plan["frame"]
        # Drop pending "ask the next question" frames above the flow (not the running go_back frame on top).
        removable = [i for i in range(frame + 1, len(stack) - 1) if stack[i].get("type") == "pattern_collect_information"]
        patch = [{"op": "remove", "path": f"/{i}"} for i in sorted(removable, reverse=True)]
        patch.append({"op": "replace", "path": f"/{frame}/step_id", "value": plan["restart_after"]})
        dispatcher.utter_message(text=t(tracker, "go_back_ok"))
        return [{"event": "stack", "update": json.dumps(patch)}] + [SlotSet(slot, None) for slot in plan["clear"]]


class ActionSkipQuestion(Action):
    """Replaces Rasa's default "let's complete this step together" when someone says "skip".

    Only the event description may be skipped; other questions get a gentle explanation.
    """

    def name(self) -> str:
        return "action_skip_question"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: dict) -> list:
        at_description_step = tracker.get_slot("event_host") is not None and tracker.get_slot("event_description") is None
        if at_description_step:
            dispatcher.utter_message(text=t(tracker, "skip_desc_ok"))
            return [SlotSet("event_description", "skip")]
        dispatcher.utter_message(text=t(tracker, "skip_required"))
        return []


class ValidateEventTime(Action):
    """Runs after the assistant collects event_time; turns "2pm" or "noon" into "2:00 PM"."""

    def name(self) -> str:
        return "validate_event_time"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: dict) -> list:
        raw = tracker.get_slot("event_time")
        if raw is None:
            return []
        start = parse_event_time(str(raw))
        if not start:
            dispatcher.utter_message(text=t(tracker, "time_unclear"))
            return [SlotSet("event_time", None)]
        return [SlotSet("event_time", start)]


class ActionReviewEvent(Action):
    def name(self) -> str:
        return "action_review_event"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: dict) -> list:
        lang = language_of(tracker)
        labels = (("event_title", "label_event"), ("event_date", "label_day"), ("event_time", "label_time"),
                  ("event_location", "label_place"), ("event_host", "label_host"), ("event_description", "label_details"))

        def shown(slot: str) -> str:
            value = tracker.get_slot(slot)
            if slot == "event_date" and value:
                return friendly_date_in(str(value), lang)
            if slot == "event_description" and (not value or is_skip(value)):
                return t(lang, "none_optional")
            return str(value) if value else t(lang, "not_provided")

        summary = t(lang, "review_header") + "\n" + "\n".join(f"{t(lang, label)}: {shown(slot)}" for slot, label in labels)
        dispatcher.utter_message(text=summary)
        return []


def search_location(text: str) -> dict | None:
    try:
        from actions.geo import parse_location
    except ImportError:
        return None
    return parse_location(text)


class ActionSearchEvents(Action):
    def name(self) -> str:
        return "action_search_events"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: dict) -> list:
        initialize_database()
        lang = language_of(tracker)
        profile = chat_profile(tracker)
        query = tracker.latest_message.get("text") or ""
        location = search_location(query)
        ranked = rank_events(profile, query, location)
        cards = [event_card(event) for event in ranked[:6]]
        if location:
            near = [e for e in ranked if e["miles"] is not None and e["miles"] <= location["radius"]]
            key = ("found_near_one" if len(near) == 1 else "found_near") if near else "nothing_near"
            text = t(lang, key, near=len(near), radius=location["radius"], place=location["label"])
        else:
            text = t(lang, "found", n=len(ranked), shown=len(cards))
        if cards and not location and ranked[0].get("reasons"):
            text += " " + ("Top pick" if lang == "en" else "La mejor opción") + f": {ranked[0]['title']} — {reasons_text(tracker, ranked[0]['reasons'])}."
        dispatcher.utter_message(text=text, json_message={"events": cards, "location": location})
        buttons = [{"title": t(lang, "tell_about", title=c["title"]), "payload": f"Tell me more about event {c['id']}"} for c in cards[:3]]
        if buttons:
            dispatcher.utter_message(text=t(lang, "choose_more"), buttons=buttons)
        return []


class ActionGetEventDetails(Action):
    def name(self) -> str:
        return "action_get_event_details"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: dict) -> list:
        initialize_database()
        lang = language_of(tracker)
        text = tracker.latest_message.get("text") or ""
        data = find_event_in_text(text, tracker.get_slot("selected_event_id"))
        if not data:
            dispatcher.utter_message(text=t(lang, "which_event"))
            return []
        dispatcher.utter_message(
            text=t(lang, "details", title=data["title"], date=friendly_date_in(data["date"], lang),
                   time=data["time"], location=data["location"], description=data["description"][:400]),
            json_message={"events": [event_card(data)]},
            buttons=[{"title": t(lang, "details_yes"), "payload": f"Yes, I'd like to go to event {data['id']}"},
                     {"title": t(lang, "details_no"), "payload": "Not this time"}],
        )
        return [SlotSet("selected_event_id", str(data["id"]))]


class ActionSaveRsvp(Action):
    """Saves an event to My Events (the same list the website shows)."""

    def name(self) -> str:
        return "action_save_rsvp"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: dict) -> list:
        initialize_database()
        lang = language_of(tracker)
        user_id = tracker_user(tracker)
        text = tracker.latest_message.get("text") or ""
        if re.search(r"\b(not this time|no|not|cancel|skip|esta vez no|cancelar)\b", text.lower()) and not re.search(r"\bevent\s*\d", text.lower()):
            dispatcher.utter_message(text=t(lang, "no_rsvp"))
            return []
        event = find_event_in_text(text, tracker.get_slot("selected_event_id"))
        if not event:
            dispatcher.utter_message(text=t(lang, "rsvp_which"))
            return []
        with connect() as db:
            db.execute("INSERT OR IGNORE INTO rsvps (user_id, event_id) VALUES (?, ?)", (user_id, event["id"]))
        dispatcher.utter_message(text=t(lang, "rsvp_saved", title=event["title"]),
                                 json_message={"saved_event": {"id": event["id"], "title": event["title"]}})
        return [SlotSet("selected_event_id", str(event["id"]))]


def reminder_send_at(event: dict, timing: str) -> str:
    from datetime import datetime, timedelta

    start = parse_event_time(event.get("time") or "") or "9:00 AM"
    when = datetime.strptime(f"{event['date']} {start}", "%Y-%m-%d %I:%M %p")
    return (when - (timedelta(days=1) if timing == "1d" else timedelta(hours=2))).isoformat(timespec="minutes")


from actions.notify import email_ready, sms_ready  # noqa: E402  (optional email/SMS settings)


class ActionSetReminder(Action):
    """Sets a reminder for the event being discussed (or the one most recently saved)."""

    def name(self) -> str:
        return "action_set_reminder"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: dict) -> list:
        initialize_database()
        lang = language_of(tracker)
        user_id = tracker_user(tracker)
        raw = f"{tracker.get_slot('reminder_timing') or ''} {tracker.latest_message.get('text') or ''}".lower()
        if re.search(r"\b2h\b|\b(2|two|dos)\s*(hours?|horas?|hrs?)\b|\bhours?\b|\bhoras?\b", raw):
            timing = "2h"
        elif re.search(r"\b1d\b|\bday\b|\bd[ií]a\b|\bnight before\b|\bnoche anterior\b|\btomorrow\b", raw):
            timing = "1d"
        else:
            dispatcher.utter_message(text=t(lang, "reminder_when"), buttons=[
                {"title": t(lang, "reminder_1d"), "payload": t(lang, "reminder_payload_1d")},
                {"title": t(lang, "reminder_2h"), "payload": t(lang, "reminder_payload_2h")},
            ])
            return []
        event = None
        selected = tracker.get_slot("selected_event_id")
        with connect() as db:
            if selected:
                row = db.execute("SELECT * FROM events WHERE id = ?", (selected,)).fetchone()
                event = dict(row) if row else None
            if not event:
                row = db.execute(
                    "SELECT e.* FROM rsvps r JOIN events e ON e.id = r.event_id WHERE r.user_id = ? AND e.date >= ? "
                    "ORDER BY r.created_at DESC LIMIT 1", (user_id, date.today().isoformat())).fetchone()
                event = dict(row) if row else None
        events = [SlotSet("reminder_timing", None)]
        if not event:
            dispatcher.utter_message(text=t(lang, "reminder_which"))
            return events
        profile = account_profile(user_id)
        email = profile.get("reminderEmail") or profile.get("email") or ""
        phone = profile.get("phone") or ""
        channels = []
        if email and email_ready():
            channels.append(("email", email))
        if phone and sms_ready():
            channels.append(("sms", phone))
        send_at = reminder_send_at(event, timing)
        with connect() as db:
            db.execute("INSERT OR IGNORE INTO rsvps (user_id, event_id) VALUES (?, ?)", (user_id, event["id"]))
            for channel, contact in channels or [("calendar", "")]:
                db.execute(
                    "INSERT INTO reminders (owner, event_id, timing, channel, contact, send_at, status, lang) VALUES (?, ?, ?, ?, ?, ?, ?, ?) "
                    "ON CONFLICT(owner, event_id, timing, channel) DO UPDATE SET contact = excluded.contact, send_at = excluded.send_at, status = excluded.status, lang = excluded.lang",
                    (user_id, event["id"], timing, channel, contact, send_at, "pending" if channel != "calendar" else "calendar", lang),
                )
        when = t(lang, "reminder_" + timing)
        if channels:
            how = (" & " if lang == "en" else " y ").join(t(lang, "how_" + c) for c, _ in channels)
            dispatcher.utter_message(text=t(lang, "reminder_set", when=when, title=event["title"], how=how),
                                     json_message={"reminder": {"event_id": event["id"], "timing": timing}})
        else:
            dispatcher.utter_message(text=t(lang, "reminder_calendar", when=when, title=event["title"]),
                                     json_message={"reminder": {"event_id": event["id"], "timing": timing}})
        return events + [SlotSet("selected_event_id", str(event["id"]))]


class ActionSetLanguage(Action):
    """Switches the conversation language (the website sends /set_language{"lang": "es"})."""

    def name(self) -> str:
        return "action_set_language"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: dict) -> list:
        lang = None
        for entity in (tracker.latest_message or {}).get("entities") or []:
            if entity.get("entity") == "lang":
                lang = str(entity.get("value") or "").lower()[:2]
        text = (tracker.latest_message.get("text") or "").lower()
        if not lang:
            lang = "es" if re.search(r"espa[ñn]ol|spanish", text) else "en" if re.search(r"english|ingl[eé]s", text) else None
        lang = lang if lang in ("en", "es") else "en"
        silent = text.startswith("/set_language")
        if not silent:
            dispatcher.utter_message(text=t(lang, "language_set"))
        return [SlotSet("language", lang)]


class ActionUpdateInterests(Action):
    def name(self) -> str:
        return "action_update_interests"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: dict) -> list:
        text = str(tracker.get_slot("interest_text") or tracker.latest_message.get("text") or "")
        profile = profile_for(tracker_user(tracker)) or {}
        existing = profile.get("interests", "")
        if text.strip() and text.strip().lower() not in existing.lower():
            profile["interests"] = f"{existing}, {text.strip()}".strip(", ")
        values = save_profile(tracker, profile)
        cards = [event_card(event) for event in rank_events({**chat_profile(tracker), **values}, text)[:6]]
        dispatcher.utter_message(text=t(tracker, "interests_added"), json_message={"events": cards})
        return [SlotSet(key, value) for key, value in values.items()] + [SlotSet("interest_text", None)]


class ActionClearTaskSlots(Action):
    """Runs inside Rasa's cancel pattern (after its built-in action_cancel_flow) so a cancelled
    event post starts fresh next time. Named differently on purpose: reusing "action_cancel_flow"
    would replace Rasa's built-in action and leave the cancelled flow running."""

    def name(self) -> str:
        return "action_clear_task_slots"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: dict) -> list:
        return [SlotSet(slot, None) for slot in (
            "event_title", "event_date", "event_time", "event_location", "event_host", "event_description",
            "event_confirmation", "reminder_timing",
        )]


class ActionRepeatLastMessage(Action):
    def name(self) -> str:
        return "action_repeat_last_message"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: dict) -> list:
        for event in reversed(tracker.events):
            if event.get("event") == "bot" and event.get("text"):
                dispatcher.utter_message(text=event["text"])
                return []
        dispatcher.utter_message(text=t(tracker, "repeat_none"))
        return []


class ActionHandleFreeText(Action):
    def name(self) -> str:
        return "action_handle_free_text"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: dict) -> list:
        text = (tracker.latest_message.get("text") or "").lower()
        if re.search(r"\b(hello|hi|hey|hola|buenos|buenas)\b", text):
            dispatcher.utter_message(text=t(tracker, "hello"))
        elif re.search(r"help|what can you do|ayuda|qué puedes", text):
            dispatcher.utter_message(text=t(tracker, "help_short"))
        else:
            dispatcher.utter_message(text=t(tracker, "fallback_free"))
        return []


initialize_database()
