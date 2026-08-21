"""Weather, astronomy, and meteor-visibility estimates.

Python does all of the science here. Grok is not used in this file.
Hourly data is stored in a pandas DataFrame. Results are dictionaries.
"""

import math
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import requests
from astropy.coordinates import AltAz, EarthLocation, SkyCoord, get_body, get_sun
from astropy.time import Time
from astropy.utils.iers import conf as iers_conf
import astropy.units as u
from astroplan import moon_illumination

# Do not fail if the leap-second table is a little out of date.
iers_conf.auto_max_age = None

from ai.cache import ttl_cache
from ai.meteor_schema import days_from_peak, find_active_shower, load_showers
from ai.utils import (
    CITY_PART_CENTRE,
    CITY_PART_SMALL,
    SCORE_EXPLANATION,
    apply_city_part_offset,
    compass_sector,
    find_nearby_dark_sites,
    forecast_dates,
    format_date_long,
    format_hour_range,
    geocode_city,
    haversine_km,
    is_large_city,
    meteor_range_display,
    openmeteo_get,
    sky_label_for_id,
    sky_quality_id,
    sky_quality_info,
    MIN_FOREST_EXTENT_KM,
)


FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
METNO_URL = "https://api.met.no/weatherapi/locationforecast/2.0/complete"

# Astronomical night starts when the Sun is more than 18 degrees below
# the horizon. We do not use twilight hours.
ASTRONOMICAL_NIGHT_LIMIT = -18.0


def fetch_weather(latitude, longitude, timezone_name=None):
    """Download an hourly forecast (Open-Meteo, then MET Norway if needed).

    Args:
        latitude (float): city latitude.
        longitude (float): city longitude.
        timezone_name (str, optional): IANA zone from geocoding, used by MET Norway.

    Returns:
        pandas.DataFrame: local time, cloud cover (%), visibility (m).
        None if both requests failed.
    """
    try:
        weather = _fetch_weather_cached(
            round(float(latitude), 4),
            round(float(longitude), 4),
            str(timezone_name or ""),
        )
        return weather.copy()
    except (requests.RequestException, ValueError, KeyError, TypeError):
        return None


def _zone(timezone_name):
    try:
        return ZoneInfo(timezone_name or "UTC")
    except Exception:
        return ZoneInfo("UTC")


def _weather_from_openmeteo(latitude, longitude):
    """Open-Meteo 14-day hourly table. Raises if the host is busy or blocked."""
    response = openmeteo_get(
        FORECAST_URL,
        params={
            "latitude": latitude,
            "longitude": longitude,
            "hourly": (
                "cloud_cover,visibility,temperature_2m,"
                "wind_speed_10m,precipitation,relative_humidity_2m"
            ),
            "timezone": "auto",
            "forecast_days": 14,
        },
        timeout=10,
        retries=1,
    )
    data = response.json()
    if data.get("error"):
        raise ValueError(str(data.get("reason") or "Open-Meteo error"))

    hourly = data.get("hourly", {})
    times = hourly.get("time", [])
    clouds = hourly.get("cloud_cover", [])
    visibility = hourly.get("visibility", [])
    temperatures = hourly.get("temperature_2m", [])
    winds = hourly.get("wind_speed_10m", [])
    rains = hourly.get("precipitation", [])
    humidities = hourly.get("relative_humidity_2m", [])

    if len(times) == 0:
        raise ValueError("empty hourly forecast")

    tz_name = data.get("timezone", "UTC")
    tz = _zone(tz_name)

    rows = []
    for i in range(len(times)):
        local_time = pd.to_datetime(times[i])
        if local_time.tzinfo is None:
            try:
                local_time = local_time.tz_localize(tz)
            except (ValueError, TypeError):
                local_time = local_time.tz_localize("UTC")
        cloud = clouds[i] if i < len(clouds) and clouds[i] is not None else 100
        vis = visibility[i] if i < len(visibility) else None
        temp = temperatures[i] if i < len(temperatures) else None
        wind = winds[i] if i < len(winds) else None
        rain = rains[i] if i < len(rains) and rains[i] is not None else 0
        humidity = humidities[i] if i < len(humidities) else None
        rows.append(
            {
                "time": local_time,
                "cloud_cover_pct": cloud,
                "visibility_m": vis,
                "temperature_c": temp,
                "wind_speed_kmh": wind,
                "precipitation_mm": rain,
                "humidity_pct": humidity,
            }
        )

    weather = pd.DataFrame(rows)
    weather["timezone_name"] = tz_name
    return weather


def _weather_from_metno(latitude, longitude, timezone_name):
    """MET Norway forecast. Used when Open-Meteo will not answer Streamlit Cloud."""
    response = openmeteo_get(
        METNO_URL,
        params={"lat": latitude, "lon": longitude},
        timeout=20,
        retries=3,
    )
    data = response.json()
    series = data.get("properties", {}).get("timeseries", [])
    if not series:
        raise ValueError("empty MET Norway forecast")

    tz = _zone(timezone_name)
    rows = []
    for item in series:
        utc_time = pd.to_datetime(item.get("time"), utc=True)
        local_time = utc_time.tz_convert(tz)
        details = (
            item.get("data", {}).get("instant", {}).get("details", {}) or {}
        )
        next1 = (
            item.get("data", {}).get("next_1_hours", {}).get("details", {}) or {}
        )
        next6 = (
            item.get("data", {}).get("next_6_hours", {}).get("details", {}) or {}
        )
        rain = next1.get("precipitation_amount")
        if rain is None:
            rain = next6.get("precipitation_amount")
        wind_ms = details.get("wind_speed")
        wind_kmh = None if wind_ms is None else float(wind_ms) * 3.6
        cloud = details.get("cloud_area_fraction")
        rows.append(
            {
                "time": local_time,
                "cloud_cover_pct": 100 if cloud is None else cloud,
                "visibility_m": None,
                "temperature_c": details.get("air_temperature"),
                "wind_speed_kmh": wind_kmh,
                "precipitation_mm": 0 if rain is None else rain,
                "humidity_pct": details.get("relative_humidity"),
            }
        )

    weather = pd.DataFrame(rows)
    weather = weather.drop_duplicates(subset=["time"]).sort_values("time")
    weather = weather.set_index("time").resample("1h").ffill().reset_index()
    weather["timezone_name"] = timezone_name or "UTC"
    if len(weather) == 0:
        raise ValueError("empty MET Norway forecast")
    return weather


@ttl_cache(3600)
def _fetch_weather_cached(latitude, longitude, timezone_name):
    """Cached forecast. Failures are not stored; MET Norway is the fallback."""
    try:
        return _weather_from_openmeteo(latitude, longitude)
    except Exception:
        return _weather_from_metno(latitude, longitude, timezone_name)


def _altaz_frame(latitude, longitude, when):
    """Build an AltAz frame for this place and time (used by astronomy helpers).

    Args:
        latitude (float)
        longitude (float)
        when: pandas Timestamp or datetime.

    Returns:
        tuple: (astropy Time, AltAz frame)
    """
    location = EarthLocation(lat=latitude * u.deg, lon=longitude * u.deg)
    time = Time(pd.Timestamp(when).to_pydatetime())
    frame = AltAz(obstime=time, location=location)
    return time, frame


def sun_altitude(latitude, longitude, when):
    """Sun height above the horizon in degrees.

    Args:
        latitude (float)
        longitude (float)
        when: pandas Timestamp or datetime.

    Returns:
        float: altitude in degrees (negative = below the horizon).
    """
    time, frame = _altaz_frame(latitude, longitude, when)
    return float(get_sun(time).transform_to(frame).alt.deg)


def moon_altitude(latitude, longitude, when):
    """Moon height above the horizon in degrees.

    Args:
        latitude (float)
        longitude (float)
        when: pandas Timestamp or datetime.

    Returns:
        float: altitude in degrees.
    """
    time, frame = _altaz_frame(latitude, longitude, when)
    return float(get_body("moon", time).transform_to(frame).alt.deg)


def moon_illumination_frac(when):
    """Fraction of the Moon that is lit (0 = new, 1 = full).

    Args:
        when: pandas Timestamp or datetime.

    Returns:
        float: value between 0 and 1.
    """
    time = Time(pd.Timestamp(when).to_pydatetime())
    return float(moon_illumination(time))


def radiant_altitude(ra_deg, dec_deg, latitude, longitude, when):
    """Height of the meteor shower radiant above the horizon.

    Radiant coordinates are a peak-night approximation from showers.json.

    Args:
        ra_deg (float): right ascension in degrees.
        dec_deg (float): declination in degrees.
        latitude (float)
        longitude (float)
        when: pandas Timestamp or datetime.

    Returns:
        float: altitude in degrees.
    """
    time, frame = _altaz_frame(latitude, longitude, when)
    radiant = SkyCoord(ra=ra_deg * u.deg, dec=dec_deg * u.deg, frame="icrs")
    return float(radiant.transform_to(frame).alt.deg)


def zhr_for_date(shower, check_date):
    """Expected ZHR on this date using a Gaussian around the peak.

    ZHR is the same for every hour of that calendar night.

    Args:
        shower (dict or None)
        check_date (datetime.date)

    Returns:
        float: ZHR for that night, or 0 if there is no shower.
    """
    if shower is None:
        return 0.0

    offset = days_from_peak(shower, check_date)
    sigma = shower["sigma_days"]
    if sigma <= 0:
        sigma = 1.0
    zhr = shower["zhr_peak"] * math.exp(-(offset ** 2) / (2 * sigma ** 2))
    return zhr


def limiting_magnitude(lm_base, moon_alt_deg, moon_illum):
    """Sky darkness for one hour: baseline LM minus a moonlight penalty.

    Args:
        lm_base (float): from the sky-quality dropdown.
        moon_alt_deg (float): Moon altitude.
        moon_illum (float): 0 to 1.

    Returns:
        float: LM, clamped between 3.0 and 7.5.
    """
    penalty = 0.0
    if moon_alt_deg > 0:
        # A low Moon hurts less than a high, bright Moon.
        height_factor = min(1.0, moon_alt_deg / 45.0)
        penalty = moon_illum * 3.0 * height_factor

    lm = lm_base - penalty
    if lm < 3.0:
        lm = 3.0
    if lm > 7.5:
        lm = 7.5
    return lm


def hourly_visible_rate(zhr, radiant_alt_deg, r, lm, cloud_cover):
    """Estimate visible meteors for one hour (IMO-style formula).

    Returns 0 if the radiant is at or below the horizon.

    Args:
        zhr (float): shower activity that night.
        radiant_alt_deg (float): radiant height in degrees.
        r (float): population index.
        lm (float): limiting magnitude.
        cloud_cover (float): cloud percentage 0-100.

    Returns:
        float: estimated meteors in that hour.
    """
    if zhr <= 0:
        return 0.0
    if radiant_alt_deg <= 0:
        return 0.0

    radiant_alt_rad = math.radians(radiant_alt_deg)
    cloud_factor = 1 - (cloud_cover / 100.0)
    if cloud_factor < 0:
        cloud_factor = 0

    rate = zhr * math.sin(radiant_alt_rad) * (r ** (lm - 6.5)) * cloud_factor
    if rate < 0:
        return 0.0
    return rate


def night_of_date_hours(weather, night_date):
    """Hours that belong to the 'night of' night_date.

    Meteor nights run from local noon on night_date to local noon the next day.
    Example: the night of 12 August includes 02:00 on 13 August.

    Args:
        weather (pandas.DataFrame): hourly forecast.
        night_date (datetime.date)

    Returns:
        pandas.DataFrame: subset of weather rows.
    """
    tz = weather["time"].dt.tz
    noon = datetime.combine(night_date, datetime.min.time())
    start = pd.Timestamp(noon, tz=tz) + pd.Timedelta(hours=12)
    end = start + pd.Timedelta(hours=24)
    mask = (weather["time"] >= start) & (weather["time"] < end)
    return weather.loc[mask].copy()


def add_astronomy_columns(hourly, latitude, longitude, shower, lm_base, zhr):
    """Add sun, moon, radiant, LM, and R_h columns to hourly rows.

    Sun altitude is computed for every hour so we can mark astronomical night.
    Moon, radiant, and R_h are only computed for those night hours.

    Args:
        hourly (pandas.DataFrame)
        latitude (float)
        longitude (float)
        shower (dict or None)
        lm_base (float)
        zhr (float)

    Returns:
        pandas.DataFrame: same rows plus astronomy columns.
    """
    sun_alts = []
    for _, row in hourly.iterrows():
        sun_alts.append(sun_altitude(latitude, longitude, row["time"]))

    hourly = hourly.copy()
    hourly["sun_alt_deg"] = sun_alts
    hourly["is_astronomical_night"] = hourly["sun_alt_deg"] < ASTRONOMICAL_NIGHT_LIMIT

    r = 2.5
    ra = 0.0
    dec = 0.0
    if shower is not None:
        r = shower["population_index_r"]
        ra = shower["radiant_ra_deg"]
        dec = shower["radiant_dec_deg"]

    moon_alts = []
    moon_illums = []
    radiant_alts = []
    lm_values = []
    rates = []

    for _, row in hourly.iterrows():
        if not row["is_astronomical_night"]:
            moon_alts.append(0.0)
            moon_illums.append(0.0)
            radiant_alts.append(0.0)
            lm_values.append(lm_base)
            rates.append(0.0)
            continue

        when = row["time"]
        moon_alt = moon_altitude(latitude, longitude, when)
        moon_illum = moon_illumination_frac(when)
        if shower is None:
            rad_alt = 0.0
        else:
            rad_alt = radiant_altitude(ra, dec, latitude, longitude, when)
        lm = limiting_magnitude(lm_base, moon_alt, moon_illum)
        rate = hourly_visible_rate(zhr, rad_alt, r, lm, row["cloud_cover_pct"])

        moon_alts.append(moon_alt)
        moon_illums.append(moon_illum)
        radiant_alts.append(rad_alt)
        lm_values.append(lm)
        rates.append(rate)

    hourly["moon_alt_deg"] = moon_alts
    hourly["moon_illum"] = moon_illums
    hourly["radiant_alt_deg"] = radiant_alts
    hourly["lm"] = lm_values
    hourly["R_h"] = rates
    return hourly


def best_three_hour_window(night_hourly):
    """Pick the 1-3 consecutive night hours with the most estimated meteors.

    Args:
        night_hourly (pandas.DataFrame): already filtered to astronomical night.

    Returns:
        dict or None: window_start, window_end, expected_meteors, hours_used.
    """
    if night_hourly is None or len(night_hourly) == 0:
        return None

    night_hourly = night_hourly.sort_values("time").reset_index(drop=True)
    n = len(night_hourly)
    block = 3
    if n < 3:
        block = n

    best_sum = -1.0
    best_i = 0
    for i in range(0, n - block + 1):
        total = float(night_hourly.loc[i : i + block - 1, "R_h"].sum())
        if total > best_sum:
            best_sum = total
            best_i = i

    start = night_hourly.loc[best_i, "time"]
    end = night_hourly.loc[best_i + block - 1, "time"]
    return {
        "window_start": start,
        "window_end": end,
        "expected_meteors": best_sum,
        "hours_used": block,
        "window_local": format_hour_range(start, end),
    }


def comfort_conditions(weather, window_start, window_end):
    """Temperature, wind, rain, and a dress hint for the viewing window.

    Used by Grok when the user asks what to wear. Not shown on the first
    results screen.

    Args:
        weather (pandas.DataFrame)
        window_start, window_end: timestamps of the first and last hour.

    Returns:
        dict or None
    """
    if window_start is None or window_end is None or weather is None:
        return None
    if "temperature_c" not in weather.columns:
        return None

    mask = (weather["time"] >= window_start) & (weather["time"] <= window_end)
    block = weather.loc[mask]
    if len(block) == 0:
        return None

    temps = block["temperature_c"].dropna()
    winds = block["wind_speed_kmh"].dropna()
    rains = block["precipitation_mm"].fillna(0)
    hums = block["humidity_pct"].dropna()
    clouds = block["cloud_cover_pct"].dropna()

    if len(temps) == 0:
        return None

    temp_min = float(temps.min())
    temp_max = float(temps.max())
    wind = float(winds.max()) if len(winds) > 0 else 0.0
    rain = float(rains.sum())
    humidity = float(hums.mean()) if len(hums) > 0 else None
    cloud = float(clouds.mean()) if len(clouds) > 0 else None

    hint_parts = []
    if rain >= 0.5:
        hint_parts.append("expect some rain, take a waterproof layer")
    if temp_min <= 5:
        hint_parts.append("very cold: heavy coat, hat, and a warm blanket")
    elif temp_min <= 12:
        hint_parts.append("cool: warm jacket and a blanket")
    elif temp_min <= 18:
        hint_parts.append("mild: a jacket should be enough")
    else:
        hint_parts.append("quite mild: light layers")
    if wind >= 20:
        hint_parts.append("it will feel windy, so a windproof layer helps")
    if humidity is not None and humidity >= 85:
        hint_parts.append("grass may be damp, sit on a mat not a thin blanket")

    return {
        "temp_min_c": int(round(temp_min)),
        "temp_max_c": int(round(temp_max)),
        "wind_kmh": int(round(wind)),
        "rain_mm": round(rain, 1),
        "humidity_pct": int(round(humidity)) if humidity is not None else None,
        "cloud_pct": int(round(cloud)) if cloud is not None else None,
        "dress_hint": "; ".join(hint_parts),
    }


def comfort_for_nearby_place(spot, timezone_name=None):
    """Weather in the Near you window, from that place's own forecast."""
    if spot is None:
        return None
    park_weather = fetch_weather(
        spot["latitude"], spot["longitude"], timezone_name
    )
    return comfort_conditions(
        park_weather, spot.get("window_start"), spot.get("window_end")
    )


def evaluate_one_night(weather, latitude, longitude, night_date, showers, lm_base):
    """Compute shower, rates, and the best 3-hour window for one night.

    Args:
        weather (pandas.DataFrame)
        latitude (float)
        longitude (float)
        night_date (datetime.date)
        showers (list)
        lm_base (float)

    Returns:
        dict: shower name, window, expected meteors, score placeholder.
    """
    shower = find_active_shower(showers, night_date)
    zhr = zhr_for_date(shower, night_date)
    hours = night_of_date_hours(weather, night_date)
    hours = add_astronomy_columns(hours, latitude, longitude, shower, lm_base, zhr)
    night_only = hours[hours["is_astronomical_night"]].copy()
    window = best_three_hour_window(night_only)

    expected = 0.0
    window_local = None
    window_start = None
    window_end = None
    if window is not None:
        expected = window["expected_meteors"]
        window_local = window["window_local"]
        window_start = window["window_start"]
        window_end = window["window_end"]

    shower_name = None
    if shower is not None:
        shower_name = shower["name"]

    return {
        "date": night_date,
        "shower": shower_name,
        "zhr": zhr,
        "expected_meteors": expected,
        "expected_meteors_display": meteor_range_display(expected),
        "window_local": window_local,
        "window_start": window_start,
        "window_end": window_end,
        "n_night_hours": len(night_only),
        "has_window": window is not None,
    }


def evaluate_all_nights(weather, latitude, longitude, dates, showers, lm_base):
    """Run evaluate_one_night for every date in the 14-day window.

    Args:
        weather (pandas.DataFrame)
        latitude (float)
        longitude (float)
        dates (list of datetime.date)
        showers (list)
        lm_base (float)

    Returns:
        list of dict
    """
    results = []
    for night_date in dates:
        results.append(
            evaluate_one_night(
                weather, latitude, longitude, night_date, showers, lm_base
            )
        )
    return results


def add_scores(night_results):
    """Add a 0-100 score relative to the best night in the forecast.

    Args:
        night_results (list of dict)

    Returns:
        list of dict: same items with a 'score' key.
    """
    best = 0.0
    for item in night_results:
        if item["expected_meteors"] > best:
            best = item["expected_meteors"]

    for item in night_results:
        if best <= 0:
            item["score"] = 0
        else:
            item["score"] = int(round(100 * item["expected_meteors"] / best))
            if item["score"] > 100:
                item["score"] = 100
    return night_results


def find_night(night_results, night_date):
    """Return the result dict for a given date, or None.

    Args:
        night_results (list of dict)
        night_date (datetime.date)

    Returns:
        dict or None
    """
    for item in night_results:
        if item["date"] == night_date:
            return item
    return None


def nearby_better_date(night_results, selected):
    """Closest date with a higher meteor estimate than the selected night.

    Args:
        night_results (list of dict)
        selected (dict): the chosen night's result.

    Returns:
        dict or None
    """
    better = []
    for item in night_results:
        if item["date"] == selected["date"]:
            continue
        if item["expected_meteors"] > selected["expected_meteors"]:
            better.append(item)

    if len(better) == 0:
        return None

    closest = better[0]
    closest_gap = abs((closest["date"] - selected["date"]).days)
    for item in better:
        gap = abs((item["date"] - selected["date"]).days)
        if gap < closest_gap:
            closest = item
            closest_gap = gap
    return closest


def closest_shower_date(night_results, selected):
    """Closest date in the 14-day window that has an active shower.

    Args:
        night_results (list of dict)
        selected (dict)

    Returns:
        dict or None
    """
    with_shower = []
    for item in night_results:
        if item["shower"] is not None and item["date"] != selected["date"]:
            with_shower.append(item)

    if len(with_shower) == 0:
        return None

    closest = with_shower[0]
    closest_gap = abs((closest["date"] - selected["date"]).days)
    for item in with_shower:
        gap = abs((item["date"] - selected["date"]).days)
        if gap < closest_gap:
            closest = item
            closest_gap = gap
    return closest


def night_summary(item):
    """Small dict used in recommendations and Grok context.

    Args:
        item (dict): one night from evaluate_all_nights.

    Returns:
        dict
    """
    return {
        "date": item["date"].isoformat(),
        "date_label": format_date_long(item["date"]),
        "shower": item["shower"],
        "window_local": item["window_local"],
        "expected_meteors": item["expected_meteors"],
        "expected_meteors_display": item["expected_meteors_display"],
        "score": item["score"],
    }


def darker_sky_for_site(current_sky_quality, site_kind, extent_km=None):
    """Sky-quality label to use at a nearby park, forest, or village.

    Only national parks, nature reserves, and large forests count as
    countryside-dark. City parks get one step darker, not a full dark sky.

    Returns None if the user's current sky is already as dark or darker.
    """
    current_id = sky_quality_id(current_sky_quality)
    if current_id == "dark":
        return None

    real_dark = site_kind in ("national park", "nature reserve")
    if site_kind == "forest" and (
        extent_km is None or extent_km >= MIN_FOREST_EXTENT_KM
    ):
        real_dark = True
    if real_dark:
        return sky_label_for_id("dark")

    if site_kind in ("park", "forest"):
        if current_id == "downtown":
            return sky_label_for_id("city")
        if current_id == "city":
            return sky_label_for_id("suburb")
        return None

    if site_kind == "village" and current_id in ("city", "downtown"):
        return sky_label_for_id("suburb")
    return None


def _place_forecast_dict(site, better_sky, night, selected, night_results):
    """Turn one evaluated night at a nearby site into a recommendation dict."""
    city_on_date = find_night(night_results, night["date"])
    city_on_date_display = selected["expected_meteors_display"]
    if city_on_date is not None:
        city_on_date_display = city_on_date["expected_meteors_display"]
    return {
        "name": site["name"],
        "kind": site["kind"],
        "distance_km": site.get("distance_from_user_km", site.get("distance_km")),
        "sector": site.get("sector"),
        "sky_quality": better_sky,
        "latitude": site["latitude"],
        "longitude": site["longitude"],
        "maps_url": site["maps_url"],
        "named_place": True,
        "date": night["date"].isoformat(),
        "date_label": format_date_long(night["date"]),
        "different_date": night["date"] != selected["date"],
        "window_local": night["window_local"],
        "expected_meteors": night["expected_meteors"],
        "expected_meteors_display": night["expected_meteors_display"],
        "city_expected_meteors_display": selected["expected_meteors_display"],
        "city_on_that_date_meteors_display": city_on_date_display,
        "shower": night["shower"],
        "better_than_user_location": (
            night["expected_meteors"] > selected["expected_meteors"]
        ),
        "window_start": night["window_start"],
        "window_end": night["window_end"],
    }


def _best_night_at_site(site, better_sky, weather, showers, dates_to_try):
    """Evaluate a nearby site on the candidate dates; keep the best night."""
    quality = sky_quality_info(better_sky)
    best = None
    for night_date in dates_to_try:
        alt = evaluate_one_night(
            weather,
            site["latitude"],
            site["longitude"],
            night_date,
            showers,
            quality["lm_base"],
        )
        if alt["n_night_hours"] == 0 or not alt["has_window"]:
            continue
        if best is None or alt["expected_meteors"] > best["expected_meteors"]:
            best = alt
    return best


def two_other_nights(night_results, selected):
    """The two other nights in the 14-day window with the most meteors."""
    others = []
    for item in night_results:
        if item["date"] != selected["date"]:
            others.append(item)
    others.sort(key=lambda item: item["expected_meteors"], reverse=True)
    summaries = []
    for item in others[:2]:
        summaries.append(night_summary(item))
    return summaries


def _forecast_one_site(site, current_sky_quality, weather, showers, selected, night_results):
    """Forecast the selected date at one nearby site, or None."""
    better_sky = darker_sky_for_site(
        current_sky_quality, site["kind"], site.get("extent_km")
    )
    if better_sky is None:
        return None
    night = _best_night_at_site(
        site, better_sky, weather, showers, [selected["date"]]
    )
    if night is None:
        return None
    return _place_forecast_dict(site, better_sky, night, selected, night_results)


def _annotate_sites(sites, city_lat, city_lon, user_lat, user_lon):
    """Add distance from the user, from the city centre, and compass sector."""
    annotated = []
    for site in sites:
        item = dict(site)
        item["distance_from_user_km"] = int(
            round(
                haversine_km(
                    user_lat, user_lon, site["latitude"], site["longitude"]
                )
            )
        )
        item["distance_from_centre_km"] = int(
            round(
                haversine_km(
                    city_lat, city_lon, site["latitude"], site["longitude"]
                )
            )
        )
        item["sector"] = compass_sector(
            city_lat, city_lon, site["latitude"], site["longitude"]
        )
        annotated.append(item)
    return annotated


def _pick_close_site(sites, max_km=20):
    """A nearby darker place that is still a realistic trip.

    Prefers a reserve, national park, or large forest over the closest
    city park. Small towns use a shorter max distance so a 30–40 km
    reserve is not called 'near you'.
    """
    eligible = []
    for site in sites:
        dist = site["distance_from_user_km"]
        if dist >= 5 and dist <= max_km:
            eligible.append(site)
    if len(eligible) == 0:
        return None

    rank = {
        "national park": 0,
        "nature reserve": 1,
        "forest": 2,
        "village": 3,
        "park": 4,
    }
    good = []
    for site in eligible:
        if site["kind"] in ("national park", "nature reserve", "forest"):
            good.append(site)
    pool = good
    if len(pool) == 0:
        villages = []
        for site in eligible:
            if site["kind"] == "village":
                villages.append(site)
        pool = villages
    if len(pool) == 0:
        parks = []
        for site in eligible:
            if site["kind"] == "park":
                parks.append(site)
        pool = parks
    if len(pool) == 0:
        return None

    chosen = pool[0]
    for site in pool:
        site_rank = rank.get(site["kind"], 9)
        chosen_rank = rank.get(chosen["kind"], 9)
        closer = site["distance_from_user_km"] < chosen["distance_from_user_km"]
        better_kind = site_rank < chosen_rank
        same_kind = site_rank == chosen_rank
        if better_kind or (same_kind and closer):
            chosen = site
    return chosen


def _pick_around_city_sites(sites, close_site, count=5, skip_sector=None):
    """At most one darker place per side of a big city, within a short drive.

    Never repeats the side the user already picked. Does not pad with a
    second North or South. Skips a side if nothing realistic is found.
    """
    used = set()
    if close_site is not None:
        used.add(close_site["name"].strip().lower())

    skip = skip_sector
    if skip in (None, CITY_PART_SMALL):
        skip = None

    picked = []

    def take_sector(sector, min_km, max_km):
        if skip is not None and sector == skip:
            return
        options = []
        for site in sites:
            if site["name"].strip().lower() in used:
                continue
            if site["sector"] != sector:
                continue
            dist = site["distance_from_centre_km"]
            if dist < min_km or dist > max_km:
                continue
            if site["distance_from_user_km"] > 25:
                continue
            options.append(site)
        options.sort(key=lambda item: item["distance_from_centre_km"])
        if len(options) == 0:
            return
        chosen = options[0]
        picked.append(chosen)
        used.add(chosen["name"].strip().lower())

    # Inner green belt, labelled Centre even if the compass says North.
    if skip != "Centre":
        centre_options = []
        for site in sites:
            if site["name"].strip().lower() in used:
                continue
            if skip is not None and site["sector"] == skip:
                continue
            dist = site["distance_from_centre_km"]
            if dist < 8 or dist > 15:
                continue
            if site["distance_from_user_km"] > 25:
                continue
            centre_options.append(site)
        centre_options.sort(key=lambda item: item["distance_from_centre_km"])
        if len(centre_options) > 0:
            centre = dict(centre_options[0])
            centre["sector"] = "Centre"
            picked.append(centre)
            used.add(centre["name"].strip().lower())

    for sector in ["North", "East", "South", "West"]:
        if len(picked) >= count:
            break
        take_sector(sector, 8, 25)

    return picked


def _dark_sites_around(place, search_lat, search_lon, user_lat, user_lon, limit):
    """Named darker places around one pin, with distances from user and centre."""
    sites = find_nearby_dark_sites(
        search_lat,
        search_lon,
        place.get("name", ""),
        place.get("country_code", ""),
        limit=limit,
        min_gap_km=6,
    )
    return _annotate_sites(
        sites,
        place["latitude"],
        place["longitude"],
        user_lat,
        user_lon,
    )


def nearby_place_forecasts(
    place,
    user_lat,
    user_lon,
    large_city,
    current_sky_quality,
    weather,
    showers,
    selected,
    night_results,
    user_city_part=None,
):
    """A spot near the user, plus extra spots around a big city.

    Near you is searched from the user's pin (North, East, …), not the
    city centre. Other sides of town still use a centre-based list.

    All location forecasts are for the user's requested date.

    Returns:
        tuple: (close_forecast_or_None, list of around-city forecasts)
    """
    if sky_quality_id(current_sky_quality) == "dark":
        return None, []

    limit = 8
    if large_city:
        limit = 20

    near_user_sites = _dark_sites_around(
        place, user_lat, user_lon, user_lat, user_lon, limit
    )

    close_max_km = 25
    if not large_city:
        close_max_km = 20
    close_site = None
    if len(near_user_sites) > 0:
        close_site = _pick_close_site(near_user_sites, max_km=close_max_km)

    around_sites = []
    if large_city:
        from_centre = user_city_part in (
            None,
            CITY_PART_SMALL,
            CITY_PART_CENTRE,
        )
        if from_centre:
            around_pool = near_user_sites
        else:
            around_pool = _dark_sites_around(
                place,
                place["latitude"],
                place["longitude"],
                user_lat,
                user_lon,
                limit,
            )
        around_sites = _pick_around_city_sites(
            around_pool, close_site, count=5, skip_sector=user_city_part
        )

    close_forecast = None
    if close_site is not None:
        close_forecast = _forecast_one_site(
            close_site,
            current_sky_quality,
            weather,
            showers,
            selected,
            night_results,
        )

    around_forecasts = []
    for site in around_sites:
        forecast = _forecast_one_site(
            site,
            current_sky_quality,
            weather,
            showers,
            selected,
            night_results,
        )
        if forecast is not None:
            around_forecasts.append(forecast)

    return close_forecast, around_forecasts


def run_pipeline(city_name, selected_date, sky_quality, city_part=None):
    """Full calculation: city -> weather -> scores -> recommendations.

    Args:
        city_name (str): user city text.
        selected_date (datetime.date): night the user picked.
        sky_quality (str): sky-quality dropdown label.
        city_part (str, optional): small town, Centre, North, East, South, West.

    Returns:
        dict: either an error key, or the full result for the UI and Grok.
    """
    place = geocode_city(city_name)
    if place is None:
        return {"ok": False, "error": "city_not_found"}

    large_city = is_large_city(place)
    user_lat, user_lon, part_used = apply_city_part_offset(
        place["latitude"],
        place["longitude"],
        city_part,
        large_city,
    )

    weather = fetch_weather(user_lat, user_lon, place.get("timezone"))
    if weather is None:
        return {"ok": False, "error": "weather_timeout"}

    quality = sky_quality_info(sky_quality)
    showers = load_showers()
    dates = forecast_dates()

    # Keep the selected date inside the 14-day window if the calendar moved.
    if selected_date not in dates:
        selected_date = dates[0]

    night_results = evaluate_all_nights(
        weather,
        user_lat,
        user_lon,
        dates,
        showers,
        quality["lm_base"],
    )
    night_results = add_scores(night_results)
    selected = find_night(night_results, selected_date)

    if selected is None:
        return {"ok": False, "error": "no_night_hours"}

    if selected["n_night_hours"] == 0:
        return {
            "ok": False,
            "error": "no_night_hours",
            "resolved_location": place["display_name"],
        }

    other_nights = two_other_nights(night_results, selected)

    nearby_full = None
    no_shower_full = None
    if selected["shower"] is None:
        no_shower_full = closest_shower_date(night_results, selected)
    else:
        nearby_full = nearby_better_date(night_results, selected)

    close_place, around_city_places = nearby_place_forecasts(
        place,
        user_lat,
        user_lon,
        large_city,
        sky_quality,
        weather,
        showers,
        selected,
        night_results,
        user_city_part=part_used,
    )

    nearby = None
    if nearby_full is not None:
        nearby = night_summary(nearby_full)
    no_shower_rec = None
    if no_shower_full is not None:
        no_shower_rec = night_summary(no_shower_full)

    location_label = place["display_name"]
    if large_city and part_used and part_used != CITY_PART_SMALL:
        location_label = place["display_name"] + " (" + part_used + ")"

    comfort = comfort_conditions(
        weather, selected.get("window_start"), selected.get("window_end")
    )
    if close_place is not None:
        close_place["comfort_conditions"] = comfort_for_nearby_place(
            close_place, place.get("timezone")
        )
        close_place.pop("window_start", None)
        close_place.pop("window_end", None)

    return {
        "ok": True,
        "error": None,
        "city": city_name,
        "resolved_location": location_label,
        "city_part": part_used,
        "large_city": large_city,
        "latitude": user_lat,
        "longitude": user_lon,
        "timezone": place["timezone"],
        "selected_date": selected_date.isoformat(),
        "selected_date_label": format_date_long(selected_date),
        "sky_quality": sky_quality,
        "bortle": quality["bortle"],
        "lm_base": quality["lm_base"],
        "shower": selected["shower"],
        "best_window_local": selected["window_local"],
        "expected_meteors": selected["expected_meteors"],
        "expected_meteors_display": selected["expected_meteors_display"],
        "score": selected["score"],
        "score_explanation": SCORE_EXPLANATION,
        "other_nights": other_nights,
        "nearby_recommendation": nearby,
        "no_shower_recommendation": no_shower_rec,
        "close_location_recommendation": close_place,
        "around_city_recommendations": around_city_places,
        "comfort_conditions": comfort,
        "n_night_hours": selected["n_night_hours"],
    }
