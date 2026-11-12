"""Import real, upcoming Salem events into Bloom's database.

Sources
-------
* Salem Public Library: public LibCal iCal feed, no key needed (always on).
  Children's and teen programs are filtered out (see `is_for_older_adults`).
* Willamette University athletics: home games in Salem, from the Northwest
  Conference public iCal feed (nwcsports.com/calendar.ashx/calendar.ics).
* Willamette Heritage Center: public events from the museum's calendar JSON
  feed (The Events Calendar WordPress API).
* Ticketmaster Discovery API: concerts and shows near Salem, used only when
  TICKETMASTER_API_KEY is set (free key from developer.ticketmaster.com).
* Any extra iCal feeds listed in EXTRA_ICAL_FEEDS, as "Name|https://...ics"
  entries separated by commas (for example a Center 50+ feed if the City
  provides one).

Imported events are upserted by `external_id`, so re-running is safe. The
Rasa assistant and the website both read from the same table.
"""

import html
import json
import os
import re
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone

from actions.actions import connect, infer_area, infer_interest_tags, initialize_database

LIBRARY_FEED = "https://cityofsalemlibrary.libcal.com/ical_subscribe.php?src=p&cid=16811"
DAYS_AHEAD = 60
NWC_FEED = "https://nwcsports.com/calendar.ashx/calendar.ics"
HERITAGE_API = "https://www.willametteheritage.org/wp-json/tribe/events/v1/events"
USER_AGENT = "BloomCommunityApp/1.0 (+https://github.com)"
SALEM_LATLONG = "44.9429,-123.0351"


# ---------------------------------------------------------------------------
# Time helpers (Pacific time without needing tzdata in the container)
# ---------------------------------------------------------------------------
def _nth_sunday(year: int, month: int, n: int) -> date:
    d = date(year, month, 1)
    d += timedelta(days=(6 - d.weekday()) % 7)
    return d + timedelta(weeks=n - 1)


def to_pacific(utc: datetime) -> datetime:
    """US Pacific: PDT (UTC-7) from 2nd Sunday of March 2am to 1st Sunday of November 2am, else PST."""
    year = utc.year
    dst_start = datetime.combine(_nth_sunday(year, 3, 2), datetime.min.time()) + timedelta(hours=10)  # 2am PST = 10:00 UTC
    dst_end = datetime.combine(_nth_sunday(year, 11, 1), datetime.min.time()) + timedelta(hours=9)  # 2am PDT = 09:00 UTC
    naive = utc.replace(tzinfo=None)
    offset = -7 if dst_start <= naive < dst_end else -8
    return naive + timedelta(hours=offset)


def clock(dt: datetime) -> str:
    return f"{(dt.hour + 11) % 12 + 1}:{dt.minute:02d} {'AM' if dt.hour < 12 else 'PM'}"


def strip_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def fetch(url: str, timeout: int = 25) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


# ---------------------------------------------------------------------------
# Relevance for adults 60+: drop programs clearly meant for kids, teens or
# families with young children, plus closures and members-only events.
# Everything else stays (Bloom ranks, it doesn't hide).
# ---------------------------------------------------------------------------
NOT_FOR_OLDER_ADULTS = re.compile(
    r"\b(kids?|child|children|children's|teens?|tweens?|toddlers?|infants?|bab(?:y|ies)|preschool\w*|"
    r"story ?times?|storytime|lego|obob|youth|niñ[oa]s|cuentos|сказки|family fun|family storytime|"
    r"sleepover|stuffy|santa|study with snacks|read to a pet|manga|homework|"
    r"closed|closures?|members[- ]only)\b",
    re.I,
)


# Descriptions that say who a program is for ("ages 6-12", "grades 3-5", "for kids").
KID_AUDIENCE = re.compile(
    r"\bages?\s*\d{1,2}\s*(?:-|–|to|through)\s*(?:1\d|\d)\b|\bgrades?\s*(?:k|\d)\b|"
    r"\bfor (?:kids|children|teens|tweens|families with young)\b|\b(?:kids|children) and (?:their )?(?:families|caregivers)\b",
    re.I,
)


def is_for_older_adults(title: str, categories: str = "", description: str = "") -> bool:
    if NOT_FOR_OLDER_ADULTS.search(f"{title} {categories}"):
        return False
    return not KID_AUDIENCE.search(description or "")


# ---------------------------------------------------------------------------
# iCal (RFC 5545) — just enough parsing for public event feeds
# ---------------------------------------------------------------------------
def _unescape_ical(value: str) -> str:
    return value.replace("\\n", "\n").replace("\\N", "\n").replace("\\,", ",").replace("\\;", ";").replace("\\\\", "\\")


def parse_ical(raw: str) -> list[dict]:
    raw = re.sub(r"\r?\n[ \t]", "", raw)  # unfold lines
    events = []
    for block in raw.split("BEGIN:VEVENT")[1:]:
        block = block.split("END:VEVENT")[0]
        item: dict = {}
        for line in block.splitlines():
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            name, *params = key.split(";")
            item[name.upper()] = (_unescape_ical(value.strip()), params)
        events.append(item)
    return events


def ical_start(item: dict, key: str = "DTSTART") -> tuple[date, str] | None:
    if key not in item:
        return None
    value, params = item[key]
    try:
        if "VALUE=DATE" in params or re.fullmatch(r"\d{8}", value):
            return datetime.strptime(value[:8], "%Y%m%d").date(), "All day"
        if value.endswith("Z"):
            local = to_pacific(datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc))
        else:  # floating or TZID=America/Los_Angeles — already local
            local = datetime.strptime(value[:15], "%Y%m%dT%H%M%S")
        return local.date(), clock(local)
    except ValueError:
        return None


def events_from_ical(raw: str, source: str, host: str, default_needs: str, skip_categories=()) -> list[dict]:
    out = []
    today = date.today()
    horizon = today + timedelta(days=DAYS_AHEAD)
    for item in parse_ical(raw):
        start = ical_start(item)
        if not start or not today <= start[0] <= horizon:
            continue
        title = item.get("SUMMARY", ("", []))[0].strip()
        categories = item.get("CATEGORIES", ("", []))[0]
        if not title or any(c.lower() in categories.lower() for c in skip_categories):
            continue
        location = item.get("LOCATION", ("", []))[0].strip() or host
        description = strip_html(item.get("DESCRIPTION", ("", []))[0])[:600]
        if not is_for_older_adults(title, categories, description):
            continue
        end = ical_start(item, "DTEND")
        end_time = end[1] if end and end[1] != "All day" and start[1] != "All day" else ""
        uid = item.get("UID", (f"{title}-{start[0]}", []))[0]
        tags = infer_interest_tags(title, description, categories)
        group = "large" if re.search(r"performance|presentation|concert|festival", categories + " " + title, re.I) else "small"
        out.append({
            "external_id": f"{source}:{uid}",
            "source": source,
            "title": title[:120],
            "date": start[0].isoformat(),
            "time": start[1],
            "end_time": end_time,
            "location": location[:160],
            "category": (categories.split(",")[0].strip() or "Community")[:40],
            "tags": ", ".join(tags) or "community",
            "group_size": group,
            "description": description or f"{title} at {location}.",
            "host": host,
            "area": infer_area(location) or ("downtown" if "main library" in location.lower() else ""),
            "cost": "Free",
            "needs": default_needs,
            "url": item.get("URL", ("", []))[0][:300],
        })
    return out


# ---------------------------------------------------------------------------
# Sources
# ---------------------------------------------------------------------------
def library_events() -> list[dict]:
    raw = fetch(LIBRARY_FEED).decode("utf-8", "replace")
    return events_from_ical(
        raw, "library", "Salem Public Library",
        default_needs="accessible, seating, free, bus",
        skip_categories=("Library Closures",),
    )


def willamette_athletics_events() -> list[dict]:
    """Willamette Bearcats home games in Salem (the NWC feed lists every conference school)."""
    raw = fetch(NWC_FEED).decode("utf-8", "replace")
    today = date.today()
    horizon = today + timedelta(days=DAYS_AHEAD)
    pattern = re.compile(r"^(?:\[\w\]\s*)?(?P<sport>.+?)\s+Willamette University vs\.?\s+(?P<opp>.+?)\s*$")
    venues = {
        "football": "McCulloch Stadium, Willamette University, Salem",
        "basketball": "Cone Field House, Willamette University, Salem",
        "volleyball": "Cone Field House, Willamette University, Salem",
    }
    out, seen = [], set()
    for item in parse_ical(raw):
        summary = re.sub(r"\s+", " ", item.get("SUMMARY", ("", []))[0]).strip()
        location = item.get("LOCATION", ("", []))[0]
        match = pattern.match(summary)
        start = ical_start(item)
        if not match or "salem" not in location.lower() or not start or not today <= start[0] <= horizon:
            continue
        sport, opponent = match.group("sport").strip(), match.group("opp").strip()
        key = (start[0], start[1], sport)
        if key in seen:
            continue
        seen.add(key)
        end = ical_start(item, "DTEND")
        place = next((v for k, v in venues.items() if k in sport.lower()), "Willamette University campus, Salem")
        out.append({
            "external_id": "willamette:" + item.get("UID", (summary, []))[0],
            "source": "willamette",
            "title": f"Willamette Bearcats {sport} vs. {opponent}",
            "date": start[0].isoformat(),
            "time": start[1],
            "end_time": ("~" + end[1]) if end and start[1] != "All day" else "",  # feed uses a fixed 3-hour block
            "location": place,
            "category": "Sports",
            "tags": "sports, social",
            "group_size": "large",
            "description": f"Cheer on the Willamette University Bearcats as they host {opponent} in {sport.lower()}. "
                           "College games are a relaxed, friendly outing; check the listing for tickets and seating.",
            "host": "Willamette University Athletics",
            "area": "downtown",
            "cost": "See listing",
            "needs": "accessible, seating, bus",
            "url": item.get("URL", ("", []))[0][:300],
        })
    return out


def heritage_center_events() -> list[dict]:
    """Willamette Heritage Center (Mill Street) public programs: tours, classes, exhibits, holiday events."""
    data = json.loads(fetch(HERITAGE_API))
    today = date.today()
    horizon = today + timedelta(days=DAYS_AHEAD)
    out = []
    for ev in data.get("events", []):
        try:
            start = datetime.strptime(ev["start_date"], "%Y-%m-%d %H:%M:%S")
            end = datetime.strptime(ev["end_date"], "%Y-%m-%d %H:%M:%S")
        except (KeyError, ValueError):
            continue
        if not today <= start.date() <= horizon:
            continue
        title = html.unescape(ev.get("title") or "").strip()
        description = strip_html(ev.get("description") or ev.get("excerpt") or "")[:600]
        categories = ", ".join(c.get("name", "") for c in ev.get("categories") or [])
        if not title or not is_for_older_adults(title, categories, description):
            continue
        venue = ev.get("venue") if isinstance(ev.get("venue"), dict) else {}
        location = ", ".join(filter(None, [venue.get("venue"), venue.get("address"), venue.get("city")])) \
            or "Willamette Heritage Center, 1313 Mill St SE, Salem"
        all_day = bool(ev.get("all_day"))
        tags = infer_interest_tags(title, description, categories)
        if "history" not in tags:
            tags.append("history")
        out.append({
            "external_id": f"heritage:{ev.get('id')}",
            "source": "heritage",
            "title": title[:120],
            "date": start.date().isoformat(),
            "time": "All day" if all_day else clock(start),
            "end_time": "" if all_day else clock(end),
            "location": html.unescape(location)[:160],
            "category": (categories.split(",")[0].strip() or "Museum")[:40],
            "tags": ", ".join(tags),
            "group_size": "small",
            "description": description or f"{title} at the Willamette Heritage Center.",
            "host": "Willamette Heritage Center",
            "area": "downtown",
            "cost": strip_html(ev.get("cost") or "") or "See listing",
            "needs": "",
            "url": (ev.get("url") or "")[:300],
        })
    return out


def extra_ical_events() -> list[dict]:
    out = []
    for entry in filter(None, (e.strip() for e in os.environ.get("EXTRA_ICAL_FEEDS", "").split(","))):
        name, _, url = entry.partition("|")
        if not url:
            name, url = "Community calendar", name
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "feed"
        try:
            out += events_from_ical(fetch(url).decode("utf-8", "replace"), slug, name.strip(), default_needs="")
        except Exception as error:  # one bad feed shouldn't stop the others
            print(f"real-events: feed {name!r} failed: {error}", flush=True)
    return out


def ticketmaster_events() -> list[dict]:
    key = os.environ.get("TICKETMASTER_API_KEY", "").strip()
    if not key:
        return []
    now = datetime.now(timezone.utc)
    params = {
        "apikey": key,
        "latlong": SALEM_LATLONG,
        "radius": "15",
        "unit": "miles",
        "startDateTime": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "endDateTime": (now + timedelta(days=DAYS_AHEAD)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "size": "100",
        "sort": "date,asc",
    }
    data = json.loads(fetch("https://app.ticketmaster.com/discovery/v2/events.json?" + urllib.parse.urlencode(params)))
    out = []
    for ev in data.get("_embedded", {}).get("events", []):
        start = ev.get("dates", {}).get("start", {})
        if not start.get("localDate"):
            continue
        time_text = "All day"
        if start.get("localTime"):
            time_text = clock(datetime.strptime(start["localTime"][:5], "%H:%M"))
        venue = (ev.get("_embedded", {}).get("venues") or [{}])[0]
        address = ", ".join(filter(None, [venue.get("name"), (venue.get("address") or {}).get("line1"), (venue.get("city") or {}).get("name")]))
        cls = (ev.get("classifications") or [{}])[0]
        kinds = " ".join(filter(None, [(cls.get("segment") or {}).get("name"), (cls.get("genre") or {}).get("name")]))
        prices = ev.get("priceRanges") or []
        cost = f"From ${prices[0]['min']:.0f}" if prices and prices[0].get("min") else "Tickets required"
        info = strip_html(ev.get("info") or ev.get("pleaseNote") or "")[:600]
        if not is_for_older_adults(ev.get("name", ""), kinds, info):
            continue
        tags = infer_interest_tags(ev.get("name", ""), kinds, info)
        if "music" in kinds.lower() and "music" not in tags:
            tags.append("music")
        if re.search(r"theat|arts", kinds, re.I) and "movies" not in tags:
            tags.append("movies")
        out.append({
            "external_id": f"ticketmaster:{ev['id']}",
            "source": "ticketmaster",
            "title": ev.get("name", "Event")[:120],
            "date": start["localDate"],
            "time": time_text,
            "end_time": "",
            "location": address[:160] or "Salem area",
            "category": kinds.split(" ")[0] if kinds else "Entertainment",
            "tags": ", ".join(tags) or "social",
            "group_size": "large",
            "description": info or f"{kinds or 'Live event'} at {venue.get('name', 'a local venue')}.",
            "host": venue.get("name") or "Ticketmaster listing",
            "area": infer_area(address) if "keizer" not in address.lower() else "keizer",
            "cost": cost,
            "needs": "accessible" if venue.get("accessibleSeatingDetail") else "",
            "url": ev.get("url", "")[:300],
        })
    return out


SOURCES = (
    ("library", library_events),
    ("willamette", willamette_athletics_events),
    ("heritage", heritage_center_events),
    ("ticketmaster", ticketmaster_events),
    ("extra feeds", extra_ical_events),
)


def refresh() -> dict:
    """Fetch every source and upsert into the events table. Returns counts per source."""
    initialize_database()
    counts = {}
    for name, loader in SOURCES:
        try:
            rows = loader()
        except Exception as error:
            print(f"real-events: {name} failed: {error}", flush=True)
            counts[name] = "error"
            continue
        counts[name] = len(rows)
        if not rows:
            continue
        with connect() as db:
            for row in rows:
                cols = ", ".join(row)
                updates = ", ".join(f"{c}=excluded.{c}" for c in row if c != "external_id")
                db.execute(
                    f"INSERT INTO events ({cols}) VALUES ({', '.join('?' for _ in row)}) "
                    f"ON CONFLICT(external_id) DO UPDATE SET {updates}",
                    tuple(row.values()),
                )
            # Drop listings that vanished from this feed (cancelled events), but keep RSVPs' past rows harmlessly.
            sources = {r["source"] for r in rows}
            ids = [r["external_id"] for r in rows]
            for src in sources:
                db.execute(
                    f"DELETE FROM events WHERE source = ? AND date >= ? AND external_id NOT IN ({', '.join('?' for _ in ids)})",
                    (src, date.today().isoformat(), *ids),
                )
    print(f"real-events: refreshed {counts}", flush=True)
    return counts


if __name__ == "__main__":
    print(refresh())
