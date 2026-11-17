"""Place, region and ZIP code lookup for location search, fully offline.

Data (public domain, U.S. Census Bureau 2020 Gazetteer files), bundled in actions/data/:
* us_zip_codes.csv - every ZIP Code Tabulation Area with its latitude/longitude
* us_places.csv    - every incorporated city/town and census-designated place

Bloom's real listings are Salem-focused today, but because every event stores a
latitude/longitude, adding sources anywhere in the US needs no code changes here.
"""

from __future__ import annotations

import csv
import math
import re
from functools import lru_cache
from pathlib import Path

DATA = Path(__file__).with_name("data")
HOME_STATE = "OR"

# Region names people use, mapped to the towns they cover.
REGIONS = {
    "coast": ("the Oregon Coast", ["Astoria", "Seaside", "Cannon Beach", "Manzanita", "Tillamook", "Pacific City",
                                   "Lincoln City", "Depoe Bay", "Newport", "Waldport", "Yachats", "Florence"]),
    "portland": ("the Portland area", ["Portland", "Beaverton", "Gresham", "Lake Oswego", "Tigard", "Milwaukie", "Hillsboro"]),
    "salem": ("Salem", ["Salem", "Keizer"]),
    "silverton": ("Silverton", ["Silverton", "Mount Angel"]),
    "valley": ("the Mid-Willamette Valley", ["Salem", "Keizer", "Silverton", "Independence", "Monmouth", "Albany", "Woodburn", "Stayton"]),
    "gorge": ("the Columbia River Gorge", ["Hood River", "Cascade Locks", "The Dalles"]),
    "eugene": ("the Eugene area", ["Eugene", "Springfield"]),
}
REGION_WORDS = {
    "coast": ("coast", "the coast", "oregon coast", "beach", "beaches", "costa", "la costa", "playa"),
    "portland": ("portland area", "portland metro"),
    "valley": ("willamette valley", "mid-valley", "mid valley", "the valley", "el valle"),
    "gorge": ("the gorge", "columbia gorge", "columbia river gorge"),
}
# Place names that are also everyday words; only matched after "near"/"in" etc.
COMMON_WORDS = {"echo", "drain", "union", "harbor", "sisters", "halfway", "riddle", "paisley", "sunriver", "fossil",
                "riverside", "fairview", "garden", "summit", "jasper", "maupin", "lakeside", "rainier", "carlton",
                "independence", "dallas", "monument", "lebanon", "sweet home", "happy valley", "falls city",
                "keno", "hines", "plush", "adrian", "jordan valley", "irrigon", "long creek", "warren", "west salem"}


def miles_between(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = math.pi / 180
    a = math.sin((lat2 - lat1) * r / 2) ** 2 + math.cos(lat1 * r) * math.cos(lat2 * r) * math.sin((lon2 - lon1) * r / 2) ** 2
    return 2 * 3958.8 * math.asin(math.sqrt(a))


@lru_cache(maxsize=1)
def _zips() -> dict[str, tuple[float, float]]:
    with open(DATA / "us_zip_codes.csv", newline="") as f:
        return {row["zip"]: (float(row["lat"]), float(row["lon"])) for row in csv.DictReader(f)}


@lru_cache(maxsize=1)
def _places() -> dict[str, list[tuple[str, float, float, float]]]:
    places: dict[str, list] = {}
    with open(DATA / "us_places.csv", newline="", encoding="utf-8", errors="replace") as f:
        for row in csv.DictReader(f):
            places.setdefault(row["name"].lower(), []).append(
                (row["state"], float(row["lat"]), float(row["lon"]), float(row["land_sqmi"])))
    return places


def zip_point(code: str) -> tuple[float, float] | None:
    return _zips().get(code)


def place_point(name: str, state: str | None = None) -> dict | None:
    """Best match for a town name: the given state, else Oregon, else the largest place with that name."""
    options = _places().get(name.strip().lower()) or _places().get(name.strip().lower() + " city")
    if not options:
        return None
    if state:
        options = [o for o in options if o[0] == state.upper()] or options
    best = sorted(options, key=lambda o: (o[0] != (state or HOME_STATE).upper(), -o[3]))[0]
    return {"lat": best[1], "lon": best[2], "label": f"{name.strip().title()}, {best[0]}", "state": best[0]}


def region_point(key: str) -> dict:
    """A region is measured by distance to its nearest town, so "the coast" never stretches inland."""
    label, towns = REGIONS[key]
    points = [p for p in (place_point(town, HOME_STATE) for town in towns) if p]
    lat = sum(p["lat"] for p in points) / len(points)
    lon = sum(p["lon"] for p in points) / len(points)
    return {"lat": lat, "lon": lon, "label": label, "radius": 10, "towns": towns,
            "points": [[round(p["lat"], 4), round(p["lon"], 4)] for p in points]}


def distance_to(location: dict, lat: float, lon: float) -> float:
    points = location.get("points") or [[location["lat"], location["lon"]]]
    return min(miles_between(p[0], p[1], lat, lon) for p in points)


def radius_in(text: str, default: int = 10) -> int:
    m = re.search(r"\b(\d{1,3})\s*(?:mi|miles?|millas?)\b", text, re.I)
    return max(1, min(150, int(m.group(1)))) if m else default


_AFTER = re.compile(r"\b(?:near|in|around|by|close to|cerca de|en|alrededor de|por)\s+(?:the\s+|la\s+|el\s+)?"
                    r"([a-záéíóúñ][a-záéíóúñ .'-]{2,40}?)(?:\s*,\s*([a-z]{2}))?(?=$|[?.!,;]|\s+(?:this|next|on|at|for|within|today|tomorrow|tonight|esta|este|hoy|mañana)\b)",
                    re.I)


def parse_location(text: str) -> dict | None:
    """Find a place in free text: "near 97301 within 10 miles", "events on the coast", "in Silverton", "Portland, ME"."""
    raw = str(text or "")
    low = raw.lower()
    zip_m = re.search(r"\b(\d{5})\b", raw)
    if zip_m and zip_point(zip_m.group(1)):
        lat, lon = zip_point(zip_m.group(1))
        return {"lat": lat, "lon": lon, "label": zip_m.group(1), "radius": radius_in(raw), "kind": "zip"}
    for key, phrases in REGION_WORDS.items():
        if any(re.search(rf"\b{re.escape(p)}\b", low) for p in phrases):
            point = region_point(key)
            point["radius"] = radius_in(raw, point["radius"])
            point["kind"] = "region"
            return point
    for m in _AFTER.finditer(raw):
        name, state = m.group(1).strip(), m.group(2)
        words = name.split()
        for size in range(min(4, len(words)), 0, -1):  # "salem oregon" -> "salem"
            candidate = " ".join(words[:size])
            if candidate.lower() in REGIONS and not state:
                point = region_point(candidate.lower())
                point["radius"] = radius_in(raw, point["radius"])
                point["kind"] = "region"
                return point
            point = place_point(candidate, state)
            if point and candidate.lower() not in {"the", "my", "town", "morning", "evening", "afternoon", "person", "general"}:
                point["radius"] = radius_in(raw)
                point["kind"] = "place"
                return point
    # No "near/in": look for an Oregon town named anywhere in the message ("Silverton events").
    tokens = re.findall(r"[a-záéíóúñ.'-]+", low)
    for size in (3, 2, 1):
        for i in range(len(tokens) - size + 1):
            candidate = " ".join(tokens[i:i + size])
            if len(candidate) < 5 or candidate in COMMON_WORDS:
                continue
            options = _places().get(candidate)
            if options and any(o[0] == HOME_STATE for o in options):
                point = place_point(candidate, HOME_STATE)
                point["radius"] = radius_in(raw)
                point["kind"] = "place"
                return point
    return None


def lookup(query: str) -> dict | None:
    """For the website's location box: a ZIP, a region word, or a town name."""
    q = str(query or "").strip()
    if not q:
        return None
    if re.fullmatch(r"\d{5}", q):
        point = zip_point(q)
        return {"lat": point[0], "lon": point[1], "label": q, "kind": "zip"} if point else None
    low = q.lower()
    for key, phrases in REGION_WORDS.items():
        if low in phrases or low == key:
            return {**region_point(key), "kind": "region"}
    if low in REGIONS:
        return {**region_point(low), "kind": "region"}
    m = re.fullmatch(r"(.+?)\s*,\s*([a-z]{2})", q, re.I)
    if m:
        point = place_point(m.group(1), m.group(2))
    else:
        point = place_point(q)
    return {**point, "kind": "place"} if point else parse_location(q)
