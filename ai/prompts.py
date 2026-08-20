"""Instructions for Grok and a helper that turns results into chat context.

Grok must only explain numbers that Python already calculated.
"""

SYSTEM_PROMPT = """You are a friendly English-language assistant that helps people
watch shooting stars.

The page already shows the meteor forecast, viewing time, other nights,
and other places. Never repeat those. Never suggest another date, time,
or location. If asked about dates or places, say that is already on the page.

Your job is extra help only: temperature, wind, rain, humidity, what to
wear, and practical viewing tips. Use WINDOW CONDITIONS for weather.
If they ask for practical tips, use PRACTICAL TIPS FOR A MEMORABLE NIGHT
exactly; do not add extra rules. Never invent weather numbers.

Explain weather answers in short, plain English (usually 2 to 4 sentences).
"""


PRACTICAL_TIPS_FALLBACK = """You are not going to a lecture. You are going on a tiny midnight picnic with the sky. Pack like you love yourself:

- A reclining chair, sun lounger, or a soft mat. Your neck has done enough today. Look well up, not at that sad little strip of horizon.
- Dress for sitting still: a jacket, a hat, and a blanket. Gloves and wool socks if your fingers get dramatic.
- A sit-mat or tarp under you. Clear nights love to quietly soak everything.
- A thermos of hot tea, water, and a snack you will actually be excited to unwrap in the dark.
- Dim red light only. Your phone is a tiny sun and it will ruin the magic. Give your eyes 20 to 30 minutes to fall in love with the dark.

Leave the telescope at home. Meteors are shy, fast, and everywhere. Your own eyes and a wide view are the whole romance."""


def format_practical_tips(comfort=None):
    """Packing list for this viewing window's weather, not a generic lecture."""
    if not comfort:
        return PRACTICAL_TIPS_FALLBACK

    tmin = comfort.get("temp_min_c")
    tmax = comfort.get("temp_max_c")
    wind = comfort.get("wind_kmh") or 0
    rain = comfort.get("rain_mm") or 0
    humidity = comfort.get("humidity_pct")
    cloud = comfort.get("cloud_pct")

    items = [
        "A reclining chair, sun lounger, or a soft mat. Your neck has done enough today. Look well up, not at that sad little strip of horizon."
    ]

    if tmin is not None and tmax is not None:
        if tmin <= 5:
            items.append(
                "It will be properly cold in the window (about "
                + str(tmin)
                + " to "
                + str(tmax)
                + " C). Heavy coat, hat, gloves, and wool socks. Sitting still is sneakily colder than the number."
            )
        elif tmin <= 12:
            items.append(
                "It will be cool (about "
                + str(tmin)
                + " to "
                + str(tmax)
                + " C). A warm jacket, a hat, and gloves. Wool socks help because you sit still."
            )
        elif tmin <= 18:
            items.append(
                "It will be mild (about "
                + str(tmin)
                + " to "
                + str(tmax)
                + " C). A jacket should be enough. A light hat if you get chilly sitting still."
            )
        else:
            items.append(
                "It will be quite mild (about "
                + str(tmin)
                + " to "
                + str(tmax)
                + " C). Light layers. Skip the winter coat; you will overheat before the first streak."
            )

    if rain >= 0.5:
        items.append(
            "A little rain is in the forecast ("
            + str(rain)
            + " mm). A waterproof layer, and a tarp or sit-mat so you are not marinating."
        )
    elif humidity is not None and humidity >= 85:
        items.append(
            "The air is damp. A sit-mat or tarp under you so the grass does not soak your blanket."
        )
    elif tmin is not None and tmin <= 14 and (cloud is None or cloud <= 55):
        items.append(
            "A sit-mat or tarp under you. Cool, clearer nights love to quietly soak everything."
        )

    if wind >= 20:
        items.append(
            "The wind will make itself known (up to "
            + str(wind)
            + " km/h). A windproof layer, and something to keep your blanket from emigrating."
        )

    if tmin is not None and tmin <= 16:
        items.append(
            "The coziest blanket or sleeping bag you own. A thermos of hot tea, water, and a snack you will actually be excited to unwrap in the dark. Cocoa counts. Biscuits count."
        )
    else:
        items.append(
            "Water and a snack you will actually be excited to unwrap in the dark. A light blanket to sit on is plenty."
        )

    items.append(
        "Dim red light only. Your phone is a tiny sun and it will ruin the magic. Give your eyes 20 to 30 minutes to fall in love with the dark."
    )

    if tmax is not None and tmax >= 16:
        items.append(
            "Insect repellent. Mosquitoes also enjoy a good night out."
        )

    closer = (
        "Leave the telescope at home. Meteors are shy, fast, and everywhere. "
        "Your own eyes and a wide view are the whole romance."
    )
    bullets = "\n".join("- " + item for item in items)
    return (
        "You are not going to a lecture. You are going on a tiny midnight "
        "picnic with the sky. Pack like you love yourself, for *this* night:\n\n"
        + bullets
        + "\n\n"
        + closer
    )


def _place_context_line(spot, prefix):
    """One nearby place as text for Grok."""
    distance = spot.get("distance_km")
    if distance is None:
        distance_text = "nearby"
    else:
        distance_text = str(distance) + " km away"
    compared = "better than the user's location"
    if not spot.get("better_than_user_location"):
        compared = "not better than staying at the user's location"
    shower = spot.get("shower")
    if shower:
        shower_text = shower
    else:
        shower_text = "none"
    return (
        prefix
        + str(spot.get("name"))
        + " ("
        + str(spot.get("kind"))
        + ", "
        + distance_text
        + "). Side of city: "
        + str(spot.get("sector") or "unknown")
        + ". Date: "
        + str(spot.get("date_label"))
        + ". Window: "
        + str(spot.get("window_local"))
        + ". Shower: "
        + shower_text
        + ". Estimated meteors: "
        + str(spot.get("expected_meteors_display"))
        + " (user's selected night at their place: "
        + str(spot.get("city_expected_meteors_display"))
        + "). This place is "
        + compared
        + ". Map: "
        + str(spot.get("maps_url"))
    )


def format_results_context(results):
    """Turn the Python result dictionary into text for Grok.

    Args:
        results (dict): output of run_pipeline() when ok is True.

    Returns:
        str: a readable summary Grok can quote from.
    """
    lines = [
        "CALCULATED RESULTS (do not change these numbers):",
        "City entered: " + str(results.get("city")),
        "Resolved location: " + str(results.get("resolved_location")),
        "Timezone: " + str(results.get("timezone")),
        "Selected date: " + str(results.get("selected_date_label")),
        "Watching from: " + str(results.get("sky_quality")),
        "Big city: " + str(results.get("large_city")),
        "City part used: " + str(results.get("city_part")),
    ]

    shower = results.get("shower")
    if shower:
        lines.append("Active meteor shower: " + shower)
    else:
        lines.append("Active meteor shower: none on the selected date")

    lines.append("Best viewing window (local time): " + str(results.get("best_window_local")))
    lines.append("Estimated visible meteors: " + str(results.get("expected_meteors_display")))
    lines.append("Score: " + str(results.get("score")) + "/100")
    lines.append("Score explanation: " + str(results.get("score_explanation")))

    other_nights = results.get("other_nights") or []
    if other_nights:
        lines.append("TWO OTHER NIGHTS (same place the user is watching from):")
        index = 1
        for item in other_nights:
            lines.append(
                str(index)
                + ". "
                + item["date_label"]
                + ", shower="
                + str(item["shower"])
                + ", window="
                + str(item["window_local"])
                + ", meteors="
                + str(item["expected_meteors_display"])
                + ", score="
                + str(item["score"])
                + "/100"
            )
            index += 1
    else:
        lines.append("TWO OTHER NIGHTS: none")

    nearby = results.get("nearby_recommendation")
    if nearby:
        lines.append(
            "Nearby better date: "
            + nearby["date_label"]
            + ", shower="
            + str(nearby["shower"])
            + ", window="
            + str(nearby["window_local"])
            + ", meteors="
            + str(nearby["expected_meteors_display"])
            + ", score="
            + str(nearby["score"])
            + "/100"
        )
    else:
        lines.append("Nearby better date: none")

    no_shower = results.get("no_shower_recommendation")
    if no_shower:
        lines.append(
            "Closest date with a shower: "
            + no_shower["date_label"]
            + ", shower="
            + str(no_shower["shower"])
            + ", window="
            + str(no_shower["window_local"])
            + ", meteors="
            + str(no_shower["expected_meteors_display"])
            + ", score="
            + str(no_shower["score"])
            + "/100"
        )

    close = results.get("close_location_recommendation")
    if close:
        lines.append(_place_context_line(close, "NEAR YOU: "))
    else:
        lines.append("NEAR YOU: none")

    around = results.get("around_city_recommendations") or []
    if len(around) == 0:
        lines.append(
            "OTHER SIDES OF THE CITY: none "
            "(only used for big cities, or none were found)."
        )
    else:
        lines.append("OTHER SIDES OF THE CITY (requested date, different sides):")
        index = 1
        for alt in around:
            lines.append(_place_context_line(alt, str(index) + ". "))
            index += 1

    comfort = results.get("comfort_conditions")
    if comfort:
        lines.append(
            "WINDOW CONDITIONS (for clothing questions; do not lead with these "
            "unless asked): temperature "
            + str(comfort.get("temp_min_c"))
            + " to "
            + str(comfort.get("temp_max_c"))
            + " C, wind up to "
            + str(comfort.get("wind_kmh"))
            + " km/h, rain "
            + str(comfort.get("rain_mm"))
            + " mm, humidity "
            + str(comfort.get("humidity_pct"))
            + "%, cloud "
            + str(comfort.get("cloud_pct"))
            + "%. Dress hint: "
            + str(comfort.get("dress_hint"))
        )
    else:
        lines.append("WINDOW CONDITIONS: none")

    lines.append(
        "PRACTICAL TIPS FOR A MEMORABLE NIGHT: " + format_practical_tips(comfort)
    )

    return "\n".join(lines)
