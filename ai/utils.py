"""Small helpers: look up a city, map sky quality, and format dates.

These functions are used by tools.py and by the Streamlit apps.
"""

import math
import time
from datetime import date, timedelta

import requests

from ai.cache import ttl_cache


GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OSM_USER_AGENT = "ShootingStarsBot/1.0 (Ironhack student project)"
WEATHER_USER_AGENT = (
    "ShootingStarsBot/1.0 (https://github.com/Sandra-Fernandez-Pascual/shooting-stars-app)"
)


def openmeteo_get(url, params, timeout=30, retries=4):
    """GET a weather API with a real User-Agent and retries on 429/5xx."""
    headers = {
        "User-Agent": WEATHER_USER_AGENT,
        "Accept": "application/json",
    }
    last_error = None
    for attempt in range(retries):
        try:
            response = requests.get(
                url, params=params, headers=headers, timeout=timeout
            )
            if response.status_code in (429, 502, 503, 504):
                last_error = requests.HTTPError(
                    "Weather HTTP " + str(response.status_code)
                )
                time.sleep(1.5 * (attempt + 1))
                continue
            response.raise_for_status()
            return response
        except requests.RequestException as err:
            last_error = err
            time.sleep(1.5 * (attempt + 1))
    if last_error is not None:
        raise last_error
    raise requests.RequestException("Weather request failed")

# How far we look for a darker viewing spot, in km.
DARK_SITE_MIN_KM = 5
DARK_SITE_MAX_KM = 30
# Pocket parks and "Tiny Forest" plantings are not dark-sky sites.
MIN_FOREST_EXTENT_KM = 1.5
MIN_PARK_EXTENT_KM = 1.2
MIN_RESERVE_EXTENT_KM = 0.5
POCKET_NAME_BITS = (
    "tiny forest",
    "tinyforest",
    "tiny-forest",
    "pocket park",
    "pocket forest",
    "miyawaki",
    "playground",
    "schoolyard",
    "school garden",
    "allotment",
    "volkstuin",
    "schooltuin",
)

# Simple place types (Bortle 2 / 4 / 6 / 8).
SKY_DARK = "Countryside"
SKY_SUBURB = "Village or suburb"
SKY_CITY = "Residential street"
SKY_DOWNTOWN = "City centre"

SKY_QUALITY_OPTIONS = [
    SKY_DARK,
    SKY_SUBURB,
    SKY_CITY,
    SKY_DOWNTOWN,
]

SKY_QUALITY_MAP = {
    SKY_DARK: {"id": "dark", "bortle": 2, "lm_base": 7.0},
    SKY_SUBURB: {"id": "suburb", "bortle": 4, "lm_base": 6.0},
    SKY_CITY: {"id": "city", "bortle": 6, "lm_base": 5.0},
    SKY_DOWNTOWN: {"id": "downtown", "bortle": 8, "lm_base": 4.0},
}

# Dingle is not a Berlin suburb. Village stays close to countryside
# so a 20-meteor night in a field is still a 20-meteor night in town.
SKY_QUALITY_MAP_SMALL = {
    SKY_DARK: {"id": "dark", "bortle": 2, "lm_base": 7.0},
    SKY_SUBURB: {"id": "suburb", "bortle": 3, "lm_base": 6.9},
    SKY_CITY: {"id": "city", "bortle": 4, "lm_base": 6.0},
    SKY_DOWNTOWN: {"id": "downtown", "bortle": 5, "lm_base": 5.5},
}

SKY_QUALITY_HELP = "Brighter places hide more meteors."

# Ask for a side of town only when the place is a real city.
# Below this, N/E/S/W barely changes the forecast.
LARGE_CITY_POPULATION = 200000
CITY_PART_SMALL = "Small town or not sure"
CITY_PART_CENTRE = "Centre"
CITY_PART_OPTIONS = [
    CITY_PART_SMALL,
    CITY_PART_CENTRE,
    "North",
    "East",
    "South",
    "West",
]
CITY_PART_HELP = (
    "Leave this on 'Small town or not sure' if you live in a village or "
    "small town. In a big city, pick the side you will watch from."
)
CITY_PART_OFFSET_KM = 10

SCORE_EXPLANATION = (
    "The score is based on the shower's intensity, how high its radiant "
    "is in the sky, sky darkness, moonlight and predicted cloud cover."
)


def geocode_city(city_name):
    """Look up a city name with the Open-Meteo geocoding API.

    Args:
        city_name (str): what the user typed, for example 'Berlin'.

    Returns:
        dict or None: latitude, longitude, timezone, and a display name.
        None if the city was not found.
    """
    if city_name is None or str(city_name).strip() == "":
        return None

    try:
        return _geocode_city_cached(city_name)
    except requests.RequestException:
        return None


@ttl_cache(86400)
def _geocode_city_cached(city_name):
    """Cached Open-Meteo lookup. Network errors are not stored."""
    response = openmeteo_get(
        GEOCODING_URL,
        params={"name": city_name.strip(), "count": 1},
        timeout=20,
    )
    data = response.json()

    results = data.get("results")
    if not results:
        return None

    first = results[0]
    country = first.get("country", "")
    name = first.get("name", city_name)
    if country:
        display_name = name + ", " + country
    else:
        display_name = name

    return {
        "name": name,
        "display_name": display_name,
        "latitude": first["latitude"],
        "longitude": first["longitude"],
        "timezone": first.get("timezone", "UTC"),
        "country": country,
        "country_code": first.get("country_code", ""),
        "population": first.get("population"),
    }


def sky_quality_info(label, large_city=True):
    """Turn a sky-quality label into Bortle class and baseline LM.

    Args:
        label (str): one of SKY_QUALITY_OPTIONS.
        large_city (bool): False uses the small-town table (a village
            is not scored like a city suburb).

    Returns:
        dict: keys id, bortle, and lm_base.
    """
    table = SKY_QUALITY_MAP if large_city else SKY_QUALITY_MAP_SMALL
    return dict(table.get(label, table[SKY_SUBURB]))


def sky_quality_id(label):
    """Short id: dark, suburb, city, or downtown."""
    return sky_quality_info(label)["id"]


def sky_label_for_id(sky_id):
    """Dropdown label for an internal sky id."""
    for label, info in SKY_QUALITY_MAP.items():
        if info["id"] == sky_id:
            return label
    return SKY_SUBURB


def forecast_dates(today=None):
    """Return the 14 allowed dates: today through today + 13 days.

    Args:
        today (datetime.date, optional): defaults to the real today.

    Returns:
        list of datetime.date
    """
    if today is None:
        today = date.today()

    dates = []
    for i in range(14):
        dates.append(today + timedelta(days=i))
    return dates


def format_hour_range(start_dt, end_dt):
    """Format a viewing window as local times, for example '02:00-05:00'.

    The end time is the start of the last hour plus one hour, so a block
    02:00, 03:00, 04:00 is shown as 02:00-05:00.

    Args:
        start_dt: pandas Timestamp or datetime of the first hour.
        end_dt: pandas Timestamp or datetime of the last hour.

    Returns:
        str: local time range.
    """
    start_text = start_dt.strftime("%H:%M")
    end_plus_one = end_dt + timedelta(hours=1)
    end_text = end_plus_one.strftime("%H:%M")
    return start_text + "-" + end_text


def format_date_long(value):
    """Format a date for the UI, for example '13 August'.

    Args:
        value (datetime.date)

    Returns:
        str
    """
    return str(value.day) + " " + value.strftime("%B")


def meteor_range_display(expected):
    """Turn a float meteor count into a small integer range.

    We show about +/- 10% so the number does not look more precise
    than a forecast really is.

    Args:
        expected (float): estimated visible meteors in the window.

    Returns:
        str: for example '24-31', or '0' if nothing is expected.
    """
    if expected is None or expected <= 0:
        return "0"

    low = int(expected * 0.9)
    high = int(expected * 1.1)
    if low < 0:
        low = 0
    if high < low:
        high = low
    if high == 0 and expected > 0:
        high = 1
        low = 0
    if low == high:
        return str(high)
    return str(low) + "-" + str(high)


def haversine_km(lat1, lon1, lat2, lon2):
    """Great-circle distance between two points, in kilometres."""
    earth_radius_km = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    return 2 * earth_radius_km * math.asin(math.sqrt(a))


def is_large_city(place):
    """True if Open-Meteo population is big enough that N/E/S/W matters."""
    population = place.get("population")
    if population is None:
        return False
    try:
        return int(population) >= LARGE_CITY_POPULATION
    except (TypeError, ValueError):
        return False


def apply_city_part_offset(latitude, longitude, city_part, large_city):
    """Move the viewing point toward N/E/S/W in a big city.

    Small towns keep the geocoded centre. “Small town or not sure” and
    “Centre” also keep the centre.

    Returns:
        tuple: (latitude, longitude, part_label_actually_used)
    """
    if not large_city:
        return latitude, longitude, CITY_PART_SMALL
    if city_part is None or city_part in (CITY_PART_SMALL, CITY_PART_CENTRE):
        return latitude, longitude, CITY_PART_CENTRE

    dlat = CITY_PART_OFFSET_KM / 111.0
    cos_lat = math.cos(math.radians(latitude))
    if abs(cos_lat) < 0.2:
        cos_lat = 0.2
    dlon = CITY_PART_OFFSET_KM / (111.0 * abs(cos_lat))

    if city_part == "North":
        return latitude + dlat, longitude, city_part
    if city_part == "South":
        return latitude - dlat, longitude, city_part
    if city_part == "East":
        return latitude, longitude + dlon, city_part
    if city_part == "West":
        return latitude, longitude - dlon, city_part
    return latitude, longitude, CITY_PART_CENTRE


def compass_sector(city_lat, city_lon, site_lat, site_lon):
    """Which side of the city a site sits on: North, East, South, West, or Centre."""
    dist = haversine_km(city_lat, city_lon, site_lat, site_lon)
    if dist < 8:
        return "Centre"
    dlat_km = (site_lat - city_lat) * 111.0
    cos_lat = math.cos(math.radians(city_lat))
    if abs(cos_lat) < 0.2:
        cos_lat = 0.2
    dlon_km = (site_lon - city_lon) * 111.0 * abs(cos_lat)
    if abs(dlat_km) >= abs(dlon_km):
        if dlat_km >= 0:
            return "North"
        return "South"
    if dlon_km >= 0:
        return "East"
    return "West"


def maps_url(latitude, longitude):
    """OpenStreetMap pin for this coordinate."""
    return (
        "https://www.openstreetmap.org/?mlat="
        + str(latitude)
        + "&mlon="
        + str(longitude)
        + "#map=12/"
        + str(latitude)
        + "/"
        + str(longitude)
    )


def _pocket_name(name):
    """True for urban micro-plantings that OSM still calls a forest."""
    lowered = (name or "").strip().lower()
    for bit in POCKET_NAME_BITS:
        if bit in lowered:
            return True
    return False


def _extent_km(boundingbox, latitude):
    """Longest side of a Nominatim bounding box, in kilometres."""
    if not boundingbox or len(boundingbox) < 4:
        return None
    try:
        lat_min = float(boundingbox[0])
        lat_max = float(boundingbox[1])
        lon_min = float(boundingbox[2])
        lon_max = float(boundingbox[3])
    except (TypeError, ValueError):
        return None
    dlat = abs(lat_max - lat_min) * 111.0
    cos_lat = math.cos(math.radians(latitude))
    if abs(cos_lat) < 0.2:
        cos_lat = 0.2
    dlon = abs(lon_max - lon_min) * 111.0 * abs(cos_lat)
    return max(dlat, dlon)


def _too_small_for_kind(kind, extent_km):
    """Skip city-square parks and named trees that are not a real dark site."""
    if kind == "national park":
        return False
    if kind == "village":
        return False
    if kind == "nature reserve":
        return extent_km is not None and extent_km < MIN_RESERVE_EXTENT_KM
    if kind == "forest":
        return extent_km is None or extent_km < MIN_FOREST_EXTENT_KM
    if kind == "park":
        return extent_km is None or extent_km < MIN_PARK_EXTENT_KM
    return False


def _nominatim_kind(row, queried_kind):
    """Map OSM class/type to a site kind, or None if it is not a dark site."""
    osm_class = (row.get("class") or "").lower()
    osm_type = (row.get("type") or "").lower()
    if osm_class in ("shop", "amenity", "office", "craft", "tourism"):
        return None
    if osm_type in ("attraction", "artwork", "information", "museum"):
        return None
    if osm_type in ("national_park",) or osm_class == "boundary":
        return "national park"
    if osm_type in ("nature_reserve", "protected_area"):
        return "nature reserve"
    if osm_type in ("wood", "forest") or osm_class == "natural":
        return "forest"
    if osm_class == "landuse" and osm_type == "forest":
        return "forest"
    if osm_type == "park" or osm_class == "leisure":
        return "park"
    return queried_kind


def _candidate_dict(
    name,
    kind,
    latitude,
    longitude,
    origin_lat,
    origin_lon,
    extent_km=None,
):
    """Build a dark-site candidate, or None if it is too close, small, or far."""
    if not name or _pocket_name(name):
        return None
    if _too_small_for_kind(kind, extent_km):
        return None
    distance = haversine_km(origin_lat, origin_lon, latitude, longitude)
    if distance < DARK_SITE_MIN_KM or distance > DARK_SITE_MAX_KM:
        return None
    return {
        "name": name,
        "kind": kind,
        "latitude": latitude,
        "longitude": longitude,
        "distance_km": int(round(distance)),
        "extent_km": None if extent_km is None else round(extent_km, 1),
        "maps_url": maps_url(latitude, longitude),
    }


def _overpass_dark_sites(latitude, longitude):
    """Ask OpenStreetMap Overpass for nearby reserves, parks, and villages.

    Woods are omitted: they match too many objects and make the query slow.
    """
    around = (
        "(around:40000,"
        + str(latitude)
        + ","
        + str(longitude)
        + ")"
    )
    query = (
        "[out:json][timeout:10];"
        "("
        "nwr[\"leisure\"=\"nature_reserve\"][\"name\"]"
        + around
        + ";"
        "nwr[\"boundary\"=\"national_park\"][\"name\"]"
        + around
        + ";"
        "node[\"place\"=\"village\"][\"name\"]"
        + around
        + ";"
        ");"
        "out center 20;"
    )
    try:
        response = requests.post(
            OVERPASS_URL,
            data={"data": query},
            headers={"User-Agent": OSM_USER_AGENT},
            timeout=12,
        )
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError):
        return []

    candidates = []
    for element in data.get("elements", []):
        tags = element.get("tags") or {}
        name = tags.get("name")
        if element.get("type") == "node":
            elat = element.get("lat")
            elon = element.get("lon")
        else:
            center = element.get("center") or {}
            elat = center.get("lat")
            elon = center.get("lon")
        if elat is None or elon is None:
            continue

        if tags.get("boundary") == "national_park":
            kind = "national park"
        elif tags.get("leisure") == "nature_reserve":
            kind = "nature reserve"
        elif tags.get("place") == "village":
            kind = "village"
        else:
            kind = "park"

        candidate = _candidate_dict(
            name, kind, float(elat), float(elon), latitude, longitude
        )
        if candidate is not None:
            candidates.append(candidate)
    return candidates


def _nominatim_dark_sites(latitude, longitude, country_code):
    """Search Nominatim for a park, forest, or village nearby."""
    delta_lat = 0.45
    cos_lat = math.cos(math.radians(latitude))
    if abs(cos_lat) < 0.1:
        cos_lat = 0.1
    delta_lon = 0.45 / abs(cos_lat)
    viewbox = (
        str(longitude - delta_lon)
        + ","
        + str(latitude + delta_lat)
        + ","
        + str(longitude + delta_lon)
        + ","
        + str(latitude - delta_lat)
    )

    headers = {"User-Agent": OSM_USER_AGENT}
    queries = [
        ("national park", "national park"),
        ("nature reserve", "nature reserve"),
        ("forest", "forest"),
    ]
    candidates = []
    for query, queried_kind in queries:
        params = {
            "q": query,
            "format": "json",
            "limit": 8,
            "viewbox": viewbox,
            "bounded": 1,
        }
        if country_code:
            params["countrycodes"] = str(country_code).lower()
        try:
            response = requests.get(
                NOMINATIM_URL, params=params, headers=headers, timeout=10
            )
            response.raise_for_status()
            rows = response.json()
        except (requests.RequestException, ValueError):
            continue

        for row in rows:
            try:
                elat = float(row["lat"])
                elon = float(row["lon"])
            except (KeyError, TypeError, ValueError):
                continue
            kind = _nominatim_kind(row, queried_kind)
            if kind is None:
                continue
            name = row.get("name") or row.get("display_name", "").split(",")[0]
            extent = _extent_km(row.get("boundingbox"), elat)
            candidate = _candidate_dict(
                name,
                kind,
                elat,
                elon,
                latitude,
                longitude,
                extent_km=extent,
            )
            if candidate is not None:
                candidates.append(candidate)
    return candidates


def _unique_sites(candidates):
    """Drop duplicate place names, keeping the first of each."""
    seen = set()
    unique = []
    for item in candidates:
        key = item["name"].strip().lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


@ttl_cache(43200)
def find_nearby_dark_sites(
    latitude, longitude, city_name, country_code="", limit=3, min_gap_km=8
):
    """Several nearby darker places, spread out so they are not the same park.

    Prefers named nature reserves, national parks, and large forests.
    Skips pocket plantings such as Tiny Forest. Villages are a fallback.

    Args:
        latitude (float)
        longitude (float)
        city_name (str): the user's city, skipped if it matches a result.
        country_code (str): ISO code, used by the Nominatim fallback.
        limit (int): how many distinct places to return.

    Returns:
        list of dict: name, kind, coordinates, distance_km, maps_url.
    """
    city_lower = (city_name or "").strip().lower()
    candidates = _nominatim_dark_sites(
        latitude, longitude, country_code
    ) + _overpass_dark_sites(latitude, longitude)

    better = []
    for item in _unique_sites(candidates):
        if item["name"].strip().lower() == city_lower:
            continue
        better.append(item)

    if len(better) == 0:
        return []

    rank = {
        "national park": 0,
        "nature reserve": 1,
        "forest": 2,
        "park": 3,
        "village": 4,
    }

    def sort_key(item):
        return (rank.get(item["kind"], 9), item["distance_km"])

    better.sort(key=sort_key)

    picked = []
    for item in better:
        too_close = False
        for other in picked:
            gap = haversine_km(
                item["latitude"],
                item["longitude"],
                other["latitude"],
                other["longitude"],
            )
            if gap < min_gap_km:
                too_close = True
                break
        if too_close:
            continue
        picked.append(item)
        if len(picked) >= limit:
            break
    return picked

