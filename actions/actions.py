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
        ):
            if name not in existing:
                db.execute(f"ALTER TABLE events ADD COLUMN {name} {ddl}")
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


def event_time_period(value: str) -> str:
    parts = value.lower().split()
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
        rows = [dict(row) for row in db.execute("SELECT * FROM events")]
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
        event_day = date.fromisoformat(event["date"]).strftime("%A").lower()
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
            dispatcher.utter_message(text="Welcome back. What would you like to do today?")
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


class ActionSaveEvent(Action):
    def name(self) -> str:
        return "action_save_event"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: dict) -> list:
        initialize_database()
        confirmation = str(tracker.get_slot("event_confirmation") or "").strip().lower()
        if not (confirmation.startswith(("yes", "yep", "sure", "confirm")) or confirmation in ("post it", "that’s right", "thats right")):
            dispatcher.utter_message(text="No problem. I haven’t posted the event.")
            return []
        fields = [tracker.get_slot(key) for key in (
            "event_title", "event_date", "event_time", "event_location", "event_host", "event_description",
        )]
        if not all(fields):
            dispatcher.utter_message(text="I’m missing a detail, so I haven’t posted it. We can try again when you’re ready.")
            return []
        with connect() as db:
            cursor = db.execute(
                """INSERT INTO events (title, date, time, location, category, tags, group_size, description, host, created_by, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
                (fields[0], fields[1], fields[2], fields[3], "Community", "community", "small", fields[5], fields[4], tracker_user(tracker)),
            )
        dispatcher.utter_message(text=f"Your event, {fields[0]}, is posted. Thank you for bringing people together!", json_message={"event_created": {"id": cursor.lastrowid, "title": fields[0]}})
        return []


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
        summary = "Here’s what I have:\n" + "\n".join(
            f"{label}: {tracker.get_slot(slot) or 'not provided'}" for slot, label in labels
        )
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
        events = [event_card(event) for event in rank_events(profile, query)]
        dispatcher.utter_message(
            text=f"I found {len(events)} local events. They’re ordered by how well they may fit, and I’ve kept every option in the list.",
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
            text=f"{data['title']} is on {data['date']} at {data['time']}, at {data['location']}. {data['description']} Would you like to go to this?",
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
        cards = [event_card(event) for event in rank_events(values, text)]
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
