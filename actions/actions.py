import os
import re
import sqlite3
from datetime import date
from pathlib import Path
from typing import Any

from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher


DB_PATH = os.environ.get("COMMUNITY_DB_PATH", "/data/community.sqlite3")


def connect() -> sqlite3.Connection:
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH, timeout=10)
    db.row_factory = sqlite3.Row
    return db


EVENTS = [
    ("Salem Library Book Club", "2026-11-14", "10:30 AM", "Salem Public Library, 585 Liberty St SE", "Reading", "books, reading, discussion, small group", "small", "A relaxed conversation about this month’s book. New members are always welcome.", "Marian"),
    ("Community Garden Morning", "2026-11-15", "9:00 AM", "Minto-Brown Island Park Community Garden", "Gardening", "gardening, outdoors, nature, plants, volunteering", "small", "Help tend shared garden beds. Tools and gloves are available.", "Salem Garden Friends"),
    ("Arts and Crafts Night", "2026-11-16", "6:00 PM", "Center 50+ at 2615 Portland Rd NE", "Arts and crafts", "art, crafts, painting, creativity, social", "small", "Try a simple seasonal craft with friendly neighbors. Supplies are included.", "Diane"),
    ("Beginner Woodworking Workshop", "2026-11-17", "1:00 PM", "Salem YMCA Community Workshop", "Woodworking", "woodworking, crafts, hands-on, learning", "small", "Learn safe tool basics and make a small wooden birdhouse.", "Paul"),
    ("Riverfront Park Walking Group", "2026-11-18", "9:30 AM", "Meet at the Riverfront Park carousel", "Walking", "walking, outdoors, fitness, nature, conversation", "small", "Take an easy-paced, flat walk along the river with plenty of time to chat.", "Lynn"),
    ("Center 50+ Community Lunch", "2026-11-19", "12:00 PM", "Center 50+ at 2615 Portland Rd NE", "Lunch", "lunch, food, social, community, conversation", "large", "Share a warm lunch and meet neighbors. Please call ahead for meal options.", "Center 50+"),
    ("Couples Dance Class", "2026-11-20", "2:00 PM", "Salem Ballroom Dance Studio, 1143 Commercial St SE", "Dance", "dance, couples, music, movement, partner", "small", "A gentle beginner class for couples. No previous dance experience needed.", "Rosa"),
    ("Gentle Chair Yoga", "2026-11-21", "10:00 AM", "West Salem Library Community Room", "Yoga", "yoga, wellness, gentle exercise, relaxation, small group", "small", "A welcoming seated yoga session. Bring a water bottle; chairs are provided.", "Anita"),
    ("Birdwatching at Minto-Brown", "2026-11-22", "8:30 AM", "Minto-Brown Island Park, north parking lot", "Birdwatching", "birdwatching, birds, nature, outdoors, walking, photography", "small", "Look for local birds on an easy walk. Binoculars are welcome but not required.", "Salem Audubon"),
    ("Neighborhood Potluck", "2026-11-23", "5:30 PM", "Bush’s Pasture Park Shelter", "Food and social", "food, cooking, potluck, neighbors, social, large group", "large", "Bring a favorite dish or simply come say hello. Everyone is welcome.", "Bush Park Neighbors"),
    ("Watercolor for Beginners", "2026-11-24", "1:30 PM", "Hallie Ford Museum of Art studio", "Art", "art, painting, watercolor, creativity, learning", "small", "Explore watercolor with a local artist. Paper and paint are supplied.", "Ruth"),
    ("Board Games and Coffee", "2026-11-25", "10:00 AM", "Archive Coffee & Bar, downtown Salem", "Games", "games, board games, coffee, conversation, social", "small", "Enjoy easy-to-learn games and coffee in a friendly, low-pressure group.", "George"),
    ("Community Choir Open Rehearsal", "2026-11-26", "6:30 PM", "First Congregational United Church, 700 Marion St NE", "Music", "music, singing, choir, community, large group", "large", "Come sing along or listen. All voices and experience levels are welcome.", "Salem Community Choir"),
    ("Easy-Paced Keizer Walk", "2026-11-27", "9:00 AM", "Keizer Rapids Park, main entrance", "Walking", "walking, outdoors, fitness, nature, conversation", "small", "A flat, gentle loop with benches and a short coffee stop afterward.", "Tom"),
    ("Knitting and Needlework Circle", "2026-11-28", "2:00 PM", "South Salem Senior Center, 6450 Fairway Ave SE", "Knitting", "knitting, sewing, crafts, hobbies, conversation", "small", "Bring a project or learn the basics. Friendly help and tea are available.", "Evelyn"),
    ("Salem History Talk: River and Rail", "2026-11-29", "11:00 AM", "Willamette Heritage Center, 1313 Mill St SE", "History", "history, learning, local, discussion, museum", "large", "Hear stories about Salem’s river and rail history, followed by questions.", "Willamette Heritage Center"),
    ("Couples Cooking Together", "2026-11-30", "4:00 PM", "Chemeketa Community College Culinary Classroom", "Cooking", "cooking, food, couples, partner, learning, social", "small", "Make a simple seasonal meal together. Registration includes ingredients.", "Chef Morgan"),
    ("Gentle Tai Chi in the Park", "2026-12-01", "10:00 AM", "Bush’s Pasture Park, near the conservatory", "Wellness", "tai chi, wellness, outdoors, gentle exercise, relaxation", "small", "Practice slow, comfortable movements outdoors. Beginners are welcome.", "Mei"),
    ("Holiday Wreath Making", "2026-12-02", "1:00 PM", "Keizer Cultural Center, 980 Chemawa Rd NE", "Crafts", "crafts, art, holiday, gardening, creativity", "small", "Make a seasonal wreath using greenery and simple materials.", "Keizer Arts"),
    ("Coffee and Current Events", "2026-12-03", "9:30 AM", "Gov Cup Coffee, 450 Court St NE", "Conversation", "conversation, news, coffee, discussion, social", "small", "A welcoming chat about the week’s news. All viewpoints are treated kindly.", "Janet"),
    ("Family-Friendly Park Cleanup", "2026-12-04", "9:00 AM", "Riverfront Park, meet by the Eco-Earth globe", "Volunteering", "volunteering, outdoors, community, walking, nature", "large", "Help tidy paths and gardens. Supplies and refreshments are provided.", "Friends of Salem Parks"),
    ("Intro to Digital Photography", "2026-12-05", "1:00 PM", "Salem Art Association Annex", "Photography", "photography, art, learning, technology, creativity", "small", "Learn simple ways to take better photos with a phone or camera.", "Alex"),
    ("Sunday Soup and Stories", "2026-12-06", "12:30 PM", "First Presbyterian Church, 770 Chemeketa St NE", "Food and social", "food, cooking, stories, community, social, large group", "large", "Enjoy homemade soup and share a favorite story if you would like.", "Salem Neighbors"),
    ("Bookbinding Hands-On Workshop", "2026-12-07", "2:00 PM", "Oregon State Library, 250 Winter St NE", "Arts and crafts", "books, crafts, art, learning, hands-on", "small", "Make a simple notebook and learn a little about bookmaking.", "Oregon State Library"),
    ("Gentle Stretch and Tea", "2026-12-08", "3:00 PM", "Center 50+ at 2615 Portland Rd NE", "Wellness", "wellness, gentle exercise, relaxation, tea, social", "small", "Enjoy easy seated stretches followed by tea and conversation.", "Center 50+"),
]


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
        ):
            if name not in existing:
                db.execute(f"ALTER TABLE events ADD COLUMN {name} {ddl}")
        db.execute("CREATE UNIQUE INDEX IF NOT EXISTS events_external_id ON events(external_id)")
        count = db.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        if count == 0:
            db.executemany(
                """INSERT INTO events
                (title, date, time, location, category, tags, group_size, description, host)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                EVENTS,
            )


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


def has_real_events(db: sqlite3.Connection) -> bool:
    return db.execute("SELECT 1 FROM events WHERE source NOT IN ('', 'community') LIMIT 1").fetchone() is not None


def current_events(db: sqlite3.Connection) -> list[dict[str, Any]]:
    """Events people can actually attend.

    Once real listings have been imported, the built-in sample events are retired and
    past events are dropped. Without real listings (offline, tests) the samples remain.
    """
    if has_real_events(db):
        rows = db.execute(
            "SELECT * FROM events WHERE (source != '' OR created_by IS NOT NULL) AND date >= ?",
            (date.today().isoformat(),),
        )
    else:
        rows = db.execute("SELECT * FROM events")
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


WHAT_YOU_CAN_DO = (
    "Welcome back! Here’s what I can help with:\n"
    "• Find events this week. Try “What’s on this week?”\n"
    "• Search by type. Try “Find music events” or “Find exercise classes”\n"
    "• Post your own event. Say “I want to post an event”"
)

INTEREST_KEYWORDS = {
    "gardening": ("garden", "plant", "seed", "flower", "compost"),
    "music": ("music", "concert", "sing", "choir", "band", "jazz", "ukulele", "symphony", "orchestra", "musician"),
    "crafts": ("craft", "knit", "knitting", "crochet", "quilt", "sew", "paint", "art", "artist", "pottery", "draw", "journal", "journaling"),
    "books": ("book", "read", "reader", "author", "poetry", "poem", "writing", "writer", "novel"),
    "walking": ("walk", "hike", "hiking", "nature", "bird", "birding", "trail", "park"),
    "fitness": ("yoga", "tai chi", "exercise", "fitness", "stretch", "zumba", "balance", "pilates"),
    "games": ("game", "bingo", "chess", "card", "bridge", "puzzle", "trivia", "mahjong", "cribbage", "lego"),
    "cooking": ("cook", "potluck", "baking", "recipe", "food", "lunch", "dinner", "tea"),
    "faith": ("church", "faith", "prayer", "worship", "bible", "spiritual"),
    "volunteering": ("volunteer", "food bank", "donate", "donation"),
    "learning": ("class", "workshop", "learn", "lecture", "presentation", "esl", "seminar", "course", "citizenship", "tutor"),
    "tech": ("tech", "technology", "computer", "phone", "smartphone", "tablet", "digital", "internet", "email", "laptop", "ipad"),
    "history": ("history", "historical", "museum", "heritage", "genealogy", "ancestry"),
    "dancing": ("dance", "dancing", "ballroom", "swing"),
    "health": ("health", "medicare", "wellness", "memory", "nutrition", "blood pressure", "caregiver", "dementia"),
    "sports": ("football", "basketball", "volleyball", "soccer", "baseball", "softball", "swim", "swimming",
               "bearcats", "athletics", "tennis"),
    "movies": ("movie", "film", "theater", "theatre", "play", "comedy", "cinema"),
    "family": ("kid", "child", "children", "storytime", "toddler", "preschool", "teen", "family", "families",
               "grandparent", "baby", "babies", "infant", "tween"),
    "social": ("coffee", "social", "conversation", "friendship", "club", "chat", "discussion", "gathering", "neighbor"),
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
             "confirm", "confirmed", "post", "please", "absolutely", "definitely", "of course", "sounds good",
             "looks good", "that's right", "thats right", "go ahead", "do it", "y")
NO_WORDS = ("no", "nope", "nah", "not", "don't", "dont", "cancel", "stop", "false", "wrong", "wait", "n",
            "never mind", "nevermind", "hold on")
SKIP_WORDS = ("skip", "no", "none", "nope", "nothing", "n/a", "na", "no thanks", "no thank you", "pass",
              "not really", "leave it blank", "blank", "-", "no description")
NO_DESCRIPTION = ""  # stored when the optional description is skipped


def parse_yes_no(text: Any) -> bool | None:
    """True for yes-like answers, False for no-like answers, None if unclear.

    Handles real booleans and the "True"/"False" strings the LLM command generator writes.
    "No" wins over "yes" ("yes, but no" / "not yet") so an event is never posted by mistake.
    """
    if isinstance(text, bool):
        return text
    t = re.sub(r"[^a-z' /]", " ", str(text or "").lower().replace("’", "'"))
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
    t = re.sub(r"[^a-z/ -]", " ", str(text or "").lower()).strip()
    t = re.sub(r"\s+", " ", t)
    return t in SKIP_WORDS or t.startswith(("skip", "no description", "nothing to add", "none"))


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


def rank_events(profile: dict[str, Any], query: str = "") -> list[dict[str, Any]]:
    profile_text = " ".join(
        str(profile.get(k, ""))
        for k in ("hobbies", "interests", "partner_activities")
    )
    interest_words = words(profile_text)
    query_words = words(query)
    filters = extract_filters(query)
    query_words -= {"find", "show", "events", "event", "near", "me", "please", "want", "like", "tell", "about"}
    query_words -= set(("monday tuesday wednesday thursday friday saturday sunday morning afternoon evening tonight today tomorrow").split())
    query_words -= set(words(" ".join(filters.values())))
    # Search phrases such as "find book clubs near me" also become lasting interests.
    if filters.get("category") and filters["category"] not in str(profile.get("interests", "")).lower():
        existing = str(profile.get("interests", ""))
        profile["interests"] = f"{existing}, {filters['category']}".strip(", ")
    with connect() as db:
        rows = current_events(db)
    ranked = []
    for event in rows:
        tags = words(f"{event['tags']} {event['category']} {event['title']} {event['description']}")
        matched = sorted((interest_words | query_words) & tags)
        score = len(matched) * 3
        reasons = []
        if matched:
            reasons.append(f"it connects with {', '.join(matched[:3])}")
        pref_time = str(profile.get("preferred_times", "")).lower()
        time_period = event_time_period(event["time"])
        if pref_time and time_period in pref_time:
            score += 2
            reasons.append(f"it’s in your preferred {time_period}")
        group_pref = str(profile.get("preferred_group_size", "")).lower()
        if group_pref and (("small" in group_pref and event["group_size"] == "small") or ("large" in group_pref and event["group_size"] == "large")):
            score += 2
            reasons.append(f"it has the {event['group_size']} group size you prefer")
        if filters.get("time") == time_period:
            score += 2
            reasons.append(f"it’s in the {time_period}")
        if filters.get("location") and filters["location"] in event["location"].lower():
            score += 2
            reasons.append(f"it’s in {filters['location']}")
        if filters.get("category") and filters["category"] in (event["category"] + " " + event["title"] + " " + event["tags"]).lower():
            score += 3
            reasons.append(f"it’s about {filters['category']}")
        try:
            event_day = date.fromisoformat(event["date"]).strftime("%A").lower()
        except ValueError:
            event_day = ""
        if filters.get("day") and filters["day"] == event_day:
            score += 2
            reasons.append(f"it’s on {filters['day']}")
        event["score"] = score
        event["why"] = "This may suit you because " + "; ".join(reasons) + "." if reasons else "This is a local option to explore; you may enjoy trying something new."
        ranked.append(event)
    # Human-in-the-loop: keep every event visible; relevance only changes its order.
    return sorted(ranked, key=lambda event: (-event["score"], event["date"], event["title"]))


def event_card(event: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": event["id"],
        "title": event["title"],
        "date": event["date"],
        "time": event["time"],
        "end_time": event.get("end_time") or "",
        "location": event["location"],
        "category": event["category"],
        "description": event["description"],
        "why": event.get("why", ""),
        "score": event.get("score", 0),
    }


class ActionLoadProfile(Action):
    def name(self) -> str:
        return "action_load_profile"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: dict) -> list:
        initialize_database()
        user_id = tracker.sender_id or "sample-salem-user"
        profile = profile_for(user_id)
        if profile:
            dispatcher.utter_message(text=WHAT_YOU_CAN_DO)
        else:
            dispatcher.utter_message(text="Hello, I’m glad you’re here. Let’s find out what you enjoy.")
        events = [SlotSet("user_id", user_id), SlotSet("profile_exists", profile is not None)]
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
        dispatcher.utter_message(text="Thanks for sharing. I’ve saved your preferences so I can tailor ideas for you.")
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
            dispatcher.utter_message(text="I’m sorry, something went wrong and your event was not posted. Please try again in a moment.")
            return []
        # The flow only reaches this action after a confirmed "yes" (see create_event in flows.yml);
        # this check is a second safety net so nothing is posted without a clear yes.
        if parse_yes_no(tracker.get_slot("event_confirmation")) is not True:
            dispatcher.utter_message(text="No problem. I haven’t posted the event.")
            return []
        # Website guests (sender ids "bloom-…") must create an account before sharing events.
        if is_web_guest(tracker.sender_id):
            dispatcher.utter_message(text="To share an event, please create a free Bloom account first, so neighbors know who is hosting. "
                                          "Tap “My profile”, then “Create an account”. I haven’t posted anything.")
            return []
        fields = [tracker.get_slot(key) for key in (
            "event_title", "event_date", "event_time", "event_location", "event_host",
        )]
        if not all(fields):
            dispatcher.utter_message(text="I’m missing a detail, so I haven’t posted it. We can try again when you’re ready.")
            return []
        title, raw_date, raw_time, location, host = (str(f).strip() for f in fields)
        description = str(tracker.get_slot("event_description") or "").strip()
        if is_skip(description):
            description = NO_DESCRIPTION
        day = parse_event_date(raw_date)
        start = parse_event_time(raw_time)
        if not day or day < date.today() or not start:
            dispatcher.utter_message(text="I couldn’t understand the date or time, so I haven’t posted it yet. Let’s try again. You can say something like “next Tuesday at 2 PM”.")
            return []
        tags = infer_interest_tags(title, description) or ["social"]
        try:
            with connect() as db:  # commits on success
                cursor = db.execute(
                    """INSERT INTO events (title, date, time, location, category, tags, group_size, description, host,
                                           area, cost, needs, created_by, created_at, source)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, 'community')""",
                    (title, day.isoformat(), start, location, "Community", ", ".join(tags), "small",
                     description or f"A community event hosted by {host}.", host,
                     infer_area(location), "Free", "", tracker_user(tracker)),
                )
                saved = db.execute("SELECT id FROM events WHERE id = ?", (cursor.lastrowid,)).fetchone()
            if not saved:
                raise sqlite3.DatabaseError("event row missing after insert")
        except sqlite3.Error as error:
            print(f"action_save_event: could not save event: {error}", flush=True)
            dispatcher.utter_message(text="I’m sorry, something went wrong and your event was not posted. Please try again in a moment.")
            return []
        dispatcher.utter_message(
            text=f"Your event, {title}, is posted for {friendly_date(day.isoformat())} at {start}. Neighbors can see it on the Bloom board right now. Thank you for bringing people together!",
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
            dispatcher.utter_message(text="Sorry, I didn’t catch the date. You can say “this Saturday”, “November 20”, or “11/20”.")
            return [SlotSet("event_date", None)]
        if day < date.today():
            dispatcher.utter_message(text="That date has already passed. What upcoming day will it be?")
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
            dispatcher.utter_message(text="Sorry, I didn’t catch that. Please say “yes” to post your event, or “no” to cancel.")
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


class ActionSkipQuestion(Action):
    """Replaces Rasa's default "let's complete this step together" when someone says "skip".

    Only the event description may be skipped; other questions get a gentle explanation.
    """

    def name(self) -> str:
        return "action_skip_question"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: dict) -> list:
        at_description_step = (
            tracker.get_slot("event_host") is not None and tracker.get_slot("event_description") is None
        )
        if at_description_step:
            dispatcher.utter_message(text="No problem, I’ll leave the description blank.")
            return [SlotSet("event_description", "skip")]
        dispatcher.utter_message(text="I need this one to continue. A few words is plenty, or say “cancel” to stop.")
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
            dispatcher.utter_message(text="Sorry, I didn’t catch the time. You can say “2 PM”, “10:30 in the morning”, or “noon”.")
            return [SlotSet("event_time", None)]
        return [SlotSet("event_time", start)]


class ActionReviewEvent(Action):
    def name(self) -> str:
        return "action_review_event"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: dict) -> list:
        labels = (
            ("event_title", "Event"),
            ("event_date", "Day"),
            ("event_time", "Time"),
            ("event_location", "Place"),
            ("event_host", "Host"),
            ("event_description", "Details"),
        )
        def shown(slot: str) -> str:
            value = tracker.get_slot(slot)
            if slot == "event_date" and value:
                return friendly_date(str(value))
            if slot == "event_description" and (not value or is_skip(value)):
                return "None (optional)"
            return str(value) if value else "not provided"

        summary = "Here’s what I have:\n" + "\n".join(f"{label}: {shown(slot)}" for slot, label in labels)
        dispatcher.utter_message(text=summary)
        return []


class ActionSearchEvents(Action):
    def name(self) -> str:
        return "action_search_events"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: dict) -> list:
        profile = profile_for(tracker_user(tracker)) or {}
        profile.update({key: tracker.get_slot(key) for key in (
            "hobbies", "interests", "partner_activities", "preferred_times", "preferred_group_size",
        ) if tracker.get_slot(key)})
        query = tracker.latest_message.get("text") or ""
        category = extract_filters(query).get("category")
        if category and category not in str(profile.get("interests", "")).lower():
            profile["interests"] = f"{profile.get('interests', '')}, {category}".strip(", ")
            profile = save_profile(tracker, profile)
        ranked = rank_events(profile, query)
        events = [event_card(event) for event in ranked[:8]]
        dispatcher.utter_message(
            text=(f"I found {len(ranked)} local events. Here are the {len(events)} that may fit you best. "
                  "Every event is still listed on the Bloom home page, so nothing is hidden."),
            json_message={"events": events},
        )
        buttons = [{"title": f"Tell me about {event['title']}", "payload": f"Tell me more about event {event['id']}"} for event in events[:3]]
        if buttons:
            dispatcher.utter_message(text="Choose an event to hear more:", buttons=buttons)
        return []


class ActionGetEventDetails(Action):
    def name(self) -> str:
        return "action_get_event_details"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: dict) -> list:
        initialize_database()
        text = tracker.latest_message.get("text") or ""
        match = re.search(r"\b(?:event\s*)?(\d+)\b", text)
        event_id = match.group(1) if match else tracker.get_slot("selected_event_id")
        with connect() as db:
            event = db.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone() if event_id else None
        if not event:
            dispatcher.utter_message(text="Which event would you like to hear about? You can choose a card or tell me its name.")
            return []
        data = dict(event)
        dispatcher.utter_message(
            text=f"{data['title']} is on {friendly_date(data['date'])} at {data['time']}, at {data['location']}. {data['description']} Would you like to go to this?",
            json_message={"event_details": event_card(data)},
            buttons=[{"title": "Yes, I’d like to go", "payload": f"Yes, I’d like to go to event {data['id']}"}, {"title": "Not this time", "payload": "Not this time"}],
        )
        return [SlotSet("selected_event_id", str(data["id"]))]


class ActionSaveRsvp(Action):
    def name(self) -> str:
        return "action_save_rsvp"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: dict) -> list:
        initialize_database()
        user_id = tracker_user(tracker)
        text = tracker.latest_message.get("text") or ""
        match = re.search(r"\b(?:event\s*)?(\d+)\b", text)
        event_id = match.group(1) if match else tracker.get_slot("selected_event_id")
        if re.search(r"\b(no|not|cancel|skip)\b", text.lower()):
            dispatcher.utter_message(text="No problem. I haven’t saved an RSVP.")
            return []
        if not event_id:
            dispatcher.utter_message(text="Tell me which event you’d like to attend, and I’ll save your RSVP.")
            return []
        with connect() as db:
            event = db.execute("SELECT title FROM events WHERE id = ?", (event_id,)).fetchone()
            if not event:
                dispatcher.utter_message(text="I couldn’t find that event. You can ask me to show the events again.")
                return []
            db.execute("INSERT OR IGNORE INTO rsvps (user_id, event_id) VALUES (?, ?)", (user_id, event_id))
        dispatcher.utter_message(text=f"Your RSVP for {event['title']} is saved. I hope you have a lovely time!")
        return [SlotSet("selected_event_id", str(event_id))]


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
        cards = [event_card(event) for event in rank_events(values, text)[:8]]
        dispatcher.utter_message(text="I’ve added that to your interests. Here are local events you might like, with the closest matches first.", json_message={"events": cards})
        return [SlotSet(key, value) for key, value in values.items()] + [SlotSet("interest_text", None)]


class ActionCancelFlow(Action):
    def name(self) -> str:
        return "action_cancel_flow"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: dict) -> list:
        dispatcher.utter_message(text="That’s okay. I’ve stopped that for now. What would you like to do instead?")
        return [
            SlotSet(slot, None)
            for slot in (
                "event_title",
                "event_date",
                "event_time",
                "event_location",
                "event_host",
                "event_description",
                "event_confirmation",
            )
        ]


class ActionRepeatLastMessage(Action):
    def name(self) -> str:
        return "action_repeat_last_message"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: dict) -> list:
        for event in reversed(tracker.events):
            if event.get("event") == "bot" and event.get("text"):
                dispatcher.utter_message(text=event["text"])
                return []
        dispatcher.utter_message(text="I don’t have a message to repeat yet.")
        return []


class ActionHandleFreeText(Action):
    def name(self) -> str:
        return "action_handle_free_text"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: dict) -> list:
        text = (tracker.latest_message.get("text") or "").lower()
        if any(word in text for word in ("hello", "hi ", "hey")):
            dispatcher.utter_message(text="Hello! I’m glad you stopped by. Would you like to find a local event?")
        elif "help" in text or "what can you do" in text:
            dispatcher.utter_message(text="I can help you find Salem events, learn about an event, save an RSVP, or post an event.")
        else:
            dispatcher.utter_message(text="I’m here to help you find friendly local activities. You can ask me to find events or help you post one.")
        return []


initialize_database()
