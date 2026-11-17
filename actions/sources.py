"""Event sources, known venues, and sample listings.

Every event in Bloom comes from one of these sources. Sources with a public feed
(see real_events.py) are imported live; for the others, Bloom shows clearly labelled
SAMPLE listings that link to the organization's real website, so people can check
the real schedule. A source's samples are replaced automatically whenever its live
feed returns upcoming events.

This module has no Rasa imports so the importer, the API and the tests can share it.
"""

from __future__ import annotations

import re
from datetime import date, timedelta

# key -> display name, icon, website, ranking weight, specialty interests, has_feed
SOURCES = {
    "center50": {
        "name": "Center 50+", "icon": "🌼", "weight": 3, "feed": False,
        "url": "https://www.cityofsalem.net/community/seniors-and-center-50",
        "specialty": None,  # Salem's senior center: relevant to everyone using Bloom
    },
    "library": {"name": "Salem Public Library", "icon": "📚", "weight": 1, "feed": True,
                "url": "https://cityofsalemlibrary.libcal.com/calendar", "specialty": ["books", "learning"]},
    "willamette": {"name": "Willamette University", "icon": "🏀", "weight": 0, "feed": True,
                   "url": "https://events.willamette.edu/", "specialty": ["sports", "music", "learning"]},
    "heritage": {"name": "Willamette Heritage Center", "icon": "🏛", "weight": 1, "feed": True,
                 "url": "https://www.willametteheritage.org/calendar/", "specialty": ["history", "crafts"]},
    "deepwood": {"name": "Deepwood Museum & Gardens", "icon": "🌷", "weight": 1, "feed": False,
                 "url": "https://deepwoodmuseum.org/event-calendar/", "specialty": ["gardening", "history", "walking"]},
    "lordschryver": {"name": "Lord & Schryver Conservancy", "icon": "🌿", "weight": 1, "feed": False,
                     "url": "https://lordschryver.org/", "specialty": ["gardening", "history"]},
    "pressplay": {"name": "Press Play Salem", "icon": "▶️", "weight": 0, "feed": True,
                  "url": "https://pressplaysalem.com/calendar/", "specialty": None},
    "daveinsalem": {"name": "Dave in Salem", "icon": "📰", "weight": 0, "feed": True,
                    "url": "https://daveinsalem.wordpress.com/", "specialty": None},
    "salemreporter": {"name": "Salem Reporter", "icon": "🗞", "weight": 0, "feed": False,
                      "url": "https://www.salemreporter.com/", "specialty": None},
    "travelsalem": {"name": "Travel Salem", "icon": "🧭", "weight": 0, "feed": False,
                    "url": "https://www.travelsalem.com/events/", "specialty": ["walking", "history"]},
    "salemart": {"name": "Salem Art Association", "icon": "🎨", "weight": 1, "feed": False,
                 "url": "https://salemart.org/", "specialty": ["crafts"]},
    "elsinore": {"name": "Elsinore Theatre", "icon": "🎭", "weight": 0, "feed": False,
                 "url": "https://elsinoretheatre.com/", "specialty": ["movies", "music"]},
    "community": {"name": "Neighbors", "icon": "🏡", "weight": 0, "feed": False, "url": "", "specialty": None},
}


def source_info(key: str) -> dict:
    return SOURCES.get(key) or {"name": key.replace("-", " ").title() or "Local listing", "icon": "📅",
                                "weight": 0, "feed": False, "url": "", "specialty": None}


# ---------------------------------------------------------------------------
# Known venues (approximate coordinates) so events can be searched by distance.
# ---------------------------------------------------------------------------
SALEM = (44.9429, -123.0351)
VENUES = [
    # (pattern, lat, lon, area, city)
    (r"center 50|2615 portland", 44.9628, -123.0063, "northeast", "Salem"),
    (r"west salem", 44.9478, -123.0627, "west", "Salem"),
    (r"main library|585 liberty|salem public library|anderson [ab]|loucks|collaboration studio|plaza room", 44.9369, -123.0398, "downtown", "Salem"),
    (r"heritage center|1313 mill|mission mill|thomas kay", 44.9373, -123.0276, "downtown", "Salem"),
    (r"deepwood|1116 mission", 44.9290, -123.0300, "south", "Salem"),
    (r"lord\s*&?\s*(and)?\s*schryver|gaiety hollow|545 mission", 44.9296, -123.0420, "south", "Salem"),
    (r"bush barn|bush'?s pasture|bush park|600 mission|salem art association", 44.9291, -123.0362, "south", "Salem"),
    (r"elsinore|170 high st", 44.9393, -123.0378, "downtown", "Salem"),
    (r"mcculloch", 44.9345, -123.0289, "downtown", "Salem"),
    (r"cone field|sparks center|hallie ford|willamette university|900 state", 44.9373, -123.0306, "downtown", "Salem"),
    (r"riverfront|carousel", 44.9416, -123.0466, "downtown", "Salem"),
    (r"oregon garden|silverton", 45.0002, -122.7930, "", "Silverton"),
    (r"keizer", 44.9901, -123.0262, "keizer", "Keizer"),
    (r"chemeketa cellars", 44.9406, -123.0378, "downtown", "Salem"),
    (r"venture hall", 44.9433, -123.0353, "downtown", "Salem"),
    (r"studios at the mill|willamette art center", 44.9379, -123.0262, "downtown", "Salem"),
]
_VENUE_RE = [(re.compile(p, re.I), lat, lon, area, city) for p, lat, lon, area, city in VENUES]


def locate(*texts: str) -> tuple[float, float, str, str] | None:
    """(lat, lon, area, city) for a known venue mentioned in the text, else None."""
    blob = " ".join(t or "" for t in texts)
    for pattern, lat, lon, area, city in _VENUE_RE:
        if pattern.search(blob):
            return lat, lon, area, city
    return None


# ---------------------------------------------------------------------------
# Sample listings. Dates are relative to today so they never go stale.
# Each: (source, day offset, start, end, title, tags, cost, needs, group, venue, description, ticket_url)
# ---------------------------------------------------------------------------
C50 = "Center 50+, 2615 Portland Rd NE, Salem"
SAMPLES = [
    ("center50", 1, "10:00 AM", "10:45 AM", "Chair Yoga for Every Body", "fitness, health", "Small fee, see website",
     "accessible, seating, bus, parking", "small", C50,
     "A gentle, seated yoga class for balance and flexibility. No experience needed.", ""),
    ("center50", 2, "12:30 PM", "3:00 PM", "Pinochle, Bridge & Card Games", "games, social", "Free",
     "accessible, seating, bus, parking, free", "small", C50,
     "Drop in for friendly card games. Partners are easy to find; beginners welcome.", ""),
    ("center50", 3, "10:00 AM", "11:00 AM", "French Conversation Group (Le cercle français)", "language, social, learning", "Free",
     "accessible, seating, bus, free", "small", C50,
     "Practice your French in a relaxed circle. All levels welcome, from rusty high-school French to fluent.", ""),
    ("center50", 3, "11:30 AM", "1:00 PM", "Senior Lunch & Social", "cooking, social", "Suggested donation",
     "accessible, seating, bus, parking", "large", C50,
     "A warm midday meal and good company. Call ahead for meal options.", ""),
    ("center50", 4, "10:00 AM", "11:30 AM", "Tech Help: Phones & Tablets", "tech, learning", "Free",
     "accessible, seating, bus, free", "small", C50,
     "Bring your phone or tablet and your questions. Patient volunteers help one-on-one.", ""),
    ("center50", 8, "1:00 PM", "2:00 PM", "Beginner Line Dancing", "dancing, fitness, music, social", "Small fee, see website",
     "accessible, bus, parking", "large", C50, "Easy steps to favorite songs. Chairs nearby for breaks.", ""),
    ("center50", 9, "10:00 AM", "11:00 AM", "Spanish Conversation Circle (Círculo de conversación)", "language, social", "Free",
     "accessible, seating, bus, free", "small", C50,
     "Practice Spanish with friendly neighbors. Todos los niveles son bienvenidos.", ""),
    ("center50", 10, "2:00 PM", "3:00 PM", "Meals on Wheels Volunteer Orientation", "volunteering, social", "Free",
     "accessible, seating, bus, free", "small", C50,
     "Learn how to deliver meals and friendly visits to homebound neighbors. Flexible schedules.", ""),
    ("center50", 15, "1:30 PM", "3:00 PM", "Memoir Writing Workshop", "books, learning", "Free",
     "accessible, seating, bus, free", "small", C50, "Turn your stories into short memoir pieces, with gentle prompts.", ""),
    ("deepwood", 2, "9:00 AM", "11:30 AM", "Garden Volunteer Morning in the Formal Gardens", "volunteering, gardening, walking", "Free",
     "free", "small", "Deepwood Museum & Gardens, 1116 Mission St SE, Salem",
     "Help tend Deepwood's historic gardens alongside experienced gardeners. Gloves and tools provided.", ""),
    ("deepwood", 5, "11:00 AM", "12:30 PM", "Winter Garden Walk & Tea", "gardening, walking, history", "Small fee, see website",
     "seating", "small", "Deepwood Museum & Gardens, 1116 Mission St SE, Salem",
     "A slow guided walk through the winter garden, followed by tea in the carriage house.", ""),
    ("deepwood", 12, "1:00 PM", "4:00 PM", "Holiday Open House at Deepwood", "history, social", "See website",
     "seating", "large", "Deepwood Museum & Gardens, 1116 Mission St SE, Salem",
     "The 1894 house decorated for the holidays. Docents share stories room by room.", ""),
    ("lordschryver", 4, "10:00 AM", "11:00 AM", "Gaiety Hollow Garden Tour", "gardening, history, walking", "See website",
     "", "small", "Gaiety Hollow, 545 Mission St S, Salem",
     "Tour the home garden of Lord & Schryver, the Northwest's first female landscape architecture firm.", ""),
    ("lordschryver", 9, "10:00 AM", "12:00 PM", "Pruning Workshop for Home Gardeners", "gardening, learning", "Small fee, see website",
     "", "small", "Gaiety Hollow, 545 Mission St S, Salem",
     "Hands-on winter pruning tips for roses, shrubs and small trees.", ""),
    ("lordschryver", 16, "9:00 AM", "12:00 PM", "Garden Volunteer Work Party", "volunteering, gardening", "Free",
     "free", "small", "Gaiety Hollow, 545 Mission St S, Salem",
     "Join the volunteer crew caring for this historic garden. No experience needed.", ""),
    ("willamette", 6, "4:00 PM", "5:00 PM", "Hallie Ford Museum of Art: Free Gallery Talk", "history, crafts, learning", "Free",
     "accessible, seating, free, bus", "small", "Hallie Ford Museum of Art, Willamette University, 900 State St, Salem",
     "A curator leads a short, friendly talk in the galleries. Free and open to the public.", ""),
    ("willamette", 11, "7:30 PM", "9:00 PM", "Willamette University Choirs: Holiday Concert", "music", "See website",
     "accessible, seating", "large", "Willamette University, 900 State St, Salem",
     "Student choirs perform seasonal favorites. Public welcome.", ""),
    ("travelsalem", 7, "5:00 PM", "9:00 PM", "Holiday Lights at The Oregon Garden (Silverton)", "walking, social, gardening", "See website",
     "accessible, parking", "large", "The Oregon Garden, 879 W Main St, Silverton",
     "Paved garden paths lit up for the season, about 20 minutes from Salem.", ""),
    ("travelsalem", 13, "11:00 AM", "4:00 PM", "Riverfront Carousel Holiday Rides", "social, family", "Small fee, see website",
     "accessible, seating, bus", "large", "Salem's Riverfront Carousel, 101 Front St NE, Salem",
     "Ride the hand-carved horses or just enjoy the music and lights by the river.", ""),
    ("salemart", 5, "10:00 AM", "5:00 PM", "Holiday Art Market at Bush Barn", "crafts, social", "Free",
     "accessible, free", "large", "Bush Barn Art Center, 600 Mission St SE, Salem",
     "Handmade gifts from local artists in the historic Bush Barn.", ""),
    ("salemart", 10, "1:00 PM", "3:00 PM", "Watercolor Basics for Adults", "crafts, learning", "Small fee, see website",
     "seating", "small", "Bush Barn Art Center, 600 Mission St SE, Salem",
     "A relaxed beginner class. Paper and paints provided.", ""),
    ("elsinore", 8, "2:00 PM", "4:15 PM", "Classic Film Matinee: It's a Wonderful Life", "movies", "Tickets required",
     "accessible, seating, hearing", "large", "Elsinore Theatre, 170 High St SE, Salem",
     "The holiday classic on the big screen in Salem's 1926 theatre.", "https://elsinoretheatre.com/"),
    ("elsinore", 14, "7:00 PM", "9:00 PM", "Holiday Concert on the Mighty Wurlitzer", "music", "Tickets required",
     "accessible, seating, hearing", "large", "Elsinore Theatre, 170 High St SE, Salem",
     "Seasonal music on the theatre's historic pipe organ.", "https://elsinoretheatre.com/"),
    ("salemreporter", 6, "6:00 PM", "7:30 PM", "Community Forum: Downtown Salem's Future", "learning, social", "Free",
     "accessible, seating, free", "large", "Salem Public Library, Loucks Auditorium, 585 Liberty St SE, Salem",
     "Local leaders answer questions about downtown plans. Listing via Salem Reporter's events page.", ""),
    ("daveinsalem", 4, "7:00 PM", "8:30 PM", "Salem Hardy Plant Society: Winter Garden Talk", "gardening, learning", "Free",
     "seating, free", "small", "Salem, Oregon (see listing for venue)",
     "Local gardeners share plants that shine in winter. A Dave in Salem pick.", ""),
    ("daveinsalem", 12, "7:00 PM", "8:30 PM", "Salem Peace Lecture", "learning, social", "See website",
     "seating", "large", "Salem, Oregon (see listing for venue)",
     "An evening talk and discussion. A Dave in Salem pick.", ""),
    # Only shown if their live feeds fail:
    ("library", 3, "12:00 PM", "1:00 PM", "Brown Bag Book Club", "books, social", "Free",
     "accessible, seating, free, bus", "small", "Main Library, 585 Liberty St SE, Salem",
     "Bring a lunch and talk about this month's book.", ""),
    ("pressplay", 5, "6:30 PM", "8:30 PM", "Trivia Night Downtown", "games, social", "Free",
     "", "large", "Downtown Salem", "Friendly team trivia. Come with friends or join a team there.", ""),
    ("heritage", 7, "10:00 AM", "11:30 AM", "Curator's Guided Tour", "history, learning", "See website",
     "", "small", "Willamette Heritage Center, 1313 Mill St SE, Salem",
     "Behind-the-scenes stories from the woolen mill and pioneer houses.", ""),
]


def sample_rows(source: str | None = None, today: date | None = None) -> list[dict]:
    today = today or date.today()
    rows = []
    for src, offset, start, end, title, tags, cost, needs, group, venue, desc, ticket in SAMPLES:
        if source and src != source:
            continue
        info = source_info(src)
        where = locate(venue) or (*SALEM, "", "Salem")
        slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
        rows.append({
            "external_id": f"sample:{src}:{slug}",
            "source": src,
            "title": title,
            "date": (today + timedelta(days=offset)).isoformat(),
            "time": start,
            "end_time": end,
            "location": venue,
            "category": tags.split(",")[0].strip().title(),
            "tags": tags,
            "group_size": group,
            "description": desc,
            "host": info["name"],
            "area": where[2],
            "cost": cost,
            "needs": needs,
            "url": info["url"],
            "source_url": info["url"],
            "ticket_url": ticket,
            "lat": where[0],
            "lon": where[1],
            "city": where[3],
            "is_sample": 1,
        })
    return rows


# Sample community posts (interest groups) so the Community tab isn't empty on day one.
SAMPLE_POSTS = [
    ("language", "French conversation group (Le cercle français)", "Thursdays, 10–11 AM", "Center 50+, 2615 Portland Rd NE",
     "Practice French over coffee. Every level welcome; we switch to English whenever anyone needs."),
    ("walking", "Thursday morning walking club", "Thursdays, 9 AM", "Riverfront Park, by the carousel",
     "An easy, flat loop along the river at a chatting pace. Benches along the way."),
    ("gardening", "Winter seed swap & garden chat", "First Saturday of the month, 10 AM", "West Salem Library meeting room",
     "Bring seeds or cuttings to share, or just come and learn from other gardeners."),
    ("crafts", "Knit & chat circle", "Tuesdays, 1–3 PM", "Center 50+ lounge",
     "Knitters, crocheters and beginners welcome. We're making hats for a local shelter."),
]
