"""Shooting Stars Bot — Streamlit app.

The user picks a city, a date, and sky quality. Python estimates the best
viewing time. Grok only explains those numbers in the chat below.
"""

import streamlit as st
from html import escape

st.set_page_config(
    page_title="Shooting Stars Bot",
    page_icon="✨",
    layout="centered",
    initial_sidebar_state="collapsed",
)

from ai.agent import agent
from ai.prompts import (
    ANSWER_ONLY_NEAR_YOU,
    ANSWER_ONLY_YOUR_PLACE,
    SYSTEM_PROMPT,
    ask_which_chat_place,
    format_results_context,
    format_tips_near_you,
    format_tips_your_place,
)
from ai.theme import BOT_AVATAR, USER_AVATAR, apply_starry_theme
from ai.tools import run_pipeline
from ai.utils import (
    CITY_PART_HELP,
    CITY_PART_OPTIONS,
    SKY_QUALITY_HELP,
    SKY_QUALITY_OPTIONS,
    forecast_dates,
    sky_quality_id,
)

NEAR_YOU_WORTH_IT = 20
CHAT_TIPS = "Practical tips for a memorable night"
CHAT_COLD = "How cold will it be in the viewing window, and what should I wear?"
CHAT_WIND = "Will it be windy during the viewing window?"
CHAT_RAIN = (
    "Will it rain during the viewing window? Should I take a waterproof layer?"
)
CHAT_PICK_YOUR = "Chat place: where I will watch from"
CHAT_PICK_NEAR = "Chat place: near you"
CHAT_SPARKLES = (CHAT_TIPS, CHAT_COLD, CHAT_WIND, CHAT_RAIN)


def _near_you_worth_it(close):
    """True if the darker nearby spot has enough meteors to bother going."""
    return close is not None and (close.get("expected_meteors") or 0) >= NEAR_YOU_WORTH_IT


def _main_worth_it(results):
    """True if the user's pin has enough meteors to show the forecast."""
    return results is not None and (results.get("expected_meteors") or 0) >= NEAR_YOU_WORTH_IT


def _nights_worth_showing(nights):
    """Other nights with at least NEAR_YOU_WORTH_IT meteors."""
    worth = []
    for item in nights or []:
        if (item.get("expected_meteors") or 0) >= NEAR_YOU_WORTH_IT:
            worth.append(item)
    return worth


def _offer_your_place(results):
    return _main_worth_it(results)


def _offer_near_you(results):
    return _near_you_worth_it(results.get("close_location_recommendation"))


def _is_tips_topic(topic):
    return topic == CHAT_TIPS or str(topic).startswith("Practical tips")


def _answer_chat_topic(topic, place, results, messages):
    """One packing list or one Grok weather answer, for one place only."""
    if _is_tips_topic(topic):
        if place == "near":
            return format_tips_near_you(results)
        return format_tips_your_place(results)
    lock = ANSWER_ONLY_NEAR_YOU
    if place == "your":
        lock = ANSWER_ONLY_YOUR_PLACE
    grok_messages = list(messages) + [
        {"role": "user", "content": str(topic) + "\n\n" + lock}
    ]
    return agent(grok_messages)


def _place_from_text(text, close):
    """Guess your vs near from a typed reply. None if unclear."""
    lowered = (text or "").lower()
    name = ""
    if close:
        name = str(close.get("name") or "").lower()
    if "near" in lowered or (name and name in lowered):
        return "near"
    if (
        "watch" in lowered
        or "street" in lowered
        or "my place" in lowered
        or "here" in lowered
    ):
        return "your"
    return None


def _show_near_you(close):
    """The Near you card: named darker place, distance, window, map."""
    window_bit = ""
    if close.get("window_local"):
        window_bit = ", " + str(close["window_local"])
    sector_bit = ""
    if close.get("sector"):
        sector_bit = ", " + str(close["sector"])
    st.markdown(
        '<div class="near-you"><strong>Near you</strong> · '
        + escape(str(close["name"]))
        + " ("
        + str(close["distance_km"])
        + " km"
        + escape(sector_bit)
        + escape(window_bit)
        + ", about "
        + escape(str(close["expected_meteors_display"]))
        + " meteors on "
        + escape(str(close["date_label"]))
        + ").</div>",
        unsafe_allow_html=True,
    )
    if close.get("maps_url"):
        st.markdown("[Open map](" + close["maps_url"] + ")")

apply_starry_theme()

st.title("Shooting Stars Bot")
st.caption("A little night-sky companion. Find the best hour, then get cozy.")

if "results" not in st.session_state:
    st.session_state["results"] = None
if "messages" not in st.session_state:
    st.session_state["messages"] = []
if "awaiting_chat_location" not in st.session_state:
    st.session_state["awaiting_chat_location"] = False
if "chat_topic" not in st.session_state:
    st.session_state["chat_topic"] = None

dates = forecast_dates()
min_date = dates[0]
max_date = dates[-1]

city = st.text_input("City", placeholder="Berlin")
selected_date = st.date_input(
    "Preferred date",
    value=min_date,
    min_value=min_date,
    max_value=max_date,
)
sky_quality = st.selectbox(
    "Where will you watch from?",
    SKY_QUALITY_OPTIONS,
    index=2,
    help=SKY_QUALITY_HELP,
)
city_part = st.selectbox(
    "If this is a big city, which side are you on?",
    CITY_PART_OPTIONS,
    index=0,
    help=CITY_PART_HELP,
)

st.caption(
    "A search can take about a minute while the sky math runs."
)
if st.button("Find best viewing time", type="primary"):
    if not city or city.strip() == "":
        st.error("Please enter a city.")
    else:
        with st.spinner(
            "Calculating the viewing forecast… this can take about a minute."
        ):
            results = run_pipeline(
                city.strip(), selected_date, sky_quality, city_part
            )

        if not results.get("ok"):
            error = results.get("error")
            if error == "city_not_found":
                st.error("City not found. Try a different spelling or a nearby city.")
            elif error == "weather_timeout":
                st.warning("Could not download the weather forecast. Please try again.")
            elif error == "no_night_hours":
                place = results.get("resolved_location", city)
                st.info(
                    "Almost no astronomical night hours at "
                    + str(place)
                    + " on this date (the Sun never gets 18 degrees below the horizon). "
                    "Try another date or city."
                )
            else:
                st.error("Something went wrong. Please try again.")
            st.session_state["results"] = None
            st.session_state["messages"] = []
            st.session_state["awaiting_chat_location"] = False
            st.session_state["chat_topic"] = None
        else:
            st.session_state["results"] = results
            st.session_state["awaiting_chat_location"] = False
            st.session_state["chat_topic"] = None
            close = results.get("close_location_recommendation")
            weak_night = not _main_worth_it(results)
            if weak_night and not _near_you_worth_it(close):
                st.session_state["messages"] = []
                st.session_state["awaiting_chat_location"] = False
                st.session_state["chat_topic"] = None
            else:
                context = format_results_context(results)
                if weak_night:
                    greeting = (
                        "Your street looks quiet tonight. The darker spot "
                        "above is the better bet. If you want a hand packing "
                        "for that one, those sparkles above are waiting. ✨"
                    )
                else:
                    greeting = (
                        "The sky is booked. You just have to show up a little "
                        "curious, a little bundled, and ready for a streak of light. "
                        "If you want a hand getting cozy, those sparkles above "
                        "are already waiting. ✨"
                    )
                st.session_state["messages"] = [
                    {"role": "system", "content": SYSTEM_PROMPT + "\n\n" + context},
                    {"role": "assistant", "content": greeting},
                ]

results = st.session_state.get("results")

if results and results.get("ok") and not _main_worth_it(results):
    close = results.get("close_location_recommendation")
    lights = ""
    if sky_quality_id(results.get("sky_quality")) in ("city", "downtown", "suburb"):
        lights = (
            " Light pollution from the city washes out shooting stars."
        )
    if _near_you_worth_it(close):
        st.warning(
            "This night does not look good for shooting stars at "
            + str(results["resolved_location"])
            + " on "
            + str(results["selected_date_label"])
            + "."
            + lights
            + " A darker spot nearby still looks worth it with tonight's "
            + "weather (about 20 or more meteors) — see **Near you** below."
        )
        _show_near_you(close)
    else:
        st.warning(
            "This night does not look good for shooting stars at "
            + str(results["resolved_location"])
            + " on "
            + str(results["selected_date_label"])
            + "."
            + lights
            + " Try another date in the next 14 days, or try a different location."
        )
    better_nights = _nights_worth_showing(results.get("other_nights"))
    if better_nights:
        st.caption("Other nights at this place that look better:")
        for item in better_nights:
            shower_bit = item["shower"] or "no major shower"
            st.write(
                "**"
                + item["date_label"]
                + ":** about "
                + item["expected_meteors_display"]
                + " meteors ("
                + shower_bit
                + ")."
            )

if results and results.get("ok") and _main_worth_it(results):
    st.subheader("Viewing forecast")
    st.write("**Location:** " + results["resolved_location"])
    st.write("**Date:** " + results["selected_date_label"])
    st.write("**Watching from:** " + results["sky_quality"])
    if results.get("large_city"):
        st.caption(
            "This forecast uses the "
            + str(results.get("city_part"))
            + " of the city."
        )
    else:
        st.caption("This looks like a smaller town, so the town centre was used.")

    if results["shower"]:
        st.write("**Meteor shower:** " + results["shower"])
    else:
        st.info("No major meteor shower is active on this date.")

    st.markdown(
        '<div class="sky-metrics">'
        + '<div class="sky-metric"><p class="sky-metric-label">Best viewing time</p>'
        + '<p class="sky-metric-value">'
        + escape(str(results["best_window_local"] or "—"))
        + "</p></div>"
        + '<div class="sky-metric"><p class="sky-metric-label">Estimated visible meteors</p>'
        + '<p class="sky-metric-value">'
        + escape(str(results["expected_meteors_display"]))
        + "</p></div>"
        + '<div class="sky-metric"><p class="sky-metric-label">Score</p>'
        + '<p class="sky-metric-value">'
        + escape(str(results["score"]) + "/100")
        + "</p></div></div>",
        unsafe_allow_html=True,
    )

    st.caption(results["score_explanation"])

    other_nights = _nights_worth_showing(results.get("other_nights"))
    if other_nights:
        st.subheader("Two other nights")
        if results.get("score") == 100:
            st.caption(
                "Your date is already the strongest of the next 14 days. "
                "These are the next-best nights at the same place."
            )
        for item in other_nights:
            shower_bit = item["shower"] or "no major shower"
            window_bit = item["window_local"] or "—"
            st.write(
                "**"
                + item["date_label"]
                + ":** "
                + window_bit
                + ", about "
                + item["expected_meteors_display"]
                + " meteors ("
                + shower_bit
                + "), score "
                + str(item["score"])
                + "/100."
            )

    close = results.get("close_location_recommendation")
    if _near_you_worth_it(close):
        _show_near_you(close)

    around = []
    for item in results.get("around_city_recommendations") or []:
        if (item.get("expected_meteors") or 0) >= NEAR_YOU_WORTH_IT:
            around.append(item)
    if around:
        st.subheader("Other sides of the city")
        st.caption(
            "Darker spots on other sides of "
            + results["resolved_location"]
            + "."
        )
        sides = []
        names = []
        distances = []
        windows = []
        meteors = []
        for item in around:
            sides.append(item.get("sector") or "—")
            names.append(item["name"])
            distances.append(str(item["distance_km"]) + " km")
            windows.append(item.get("window_local") or "—")
            meteors.append(item["expected_meteors_display"])
        st.dataframe(
            {
                "Side": sides,
                "Place": names,
                "From you": distances,
                "Window": windows,
                "Meteors": meteors,
            },
            hide_index=True,
        )

    no_shower = results.get("no_shower_recommendation")
    if no_shower and not results["shower"]:
        st.info(
            "Closest night with a shower: "
            + no_shower["date_label"]
            + " ("
            + str(no_shower["shower"])
            + ", "
            + str(no_shower["window_local"])
            + ", about "
            + no_shower["expected_meteors_display"]
            + " meteors)."
        )

if results and results.get("ok") and (
    _main_worth_it(results)
    or _near_you_worth_it(results.get("close_location_recommendation"))
):
    pending = st.session_state.pop("pending_chat", None)
    if pending:
        st.session_state["messages"].append(
            {"role": "user", "content": pending}
        )
        offer_your = _offer_your_place(results)
        offer_near = _offer_near_you(results)
        close = results.get("close_location_recommendation")
        kind = "tips"
        if pending in (CHAT_COLD, CHAT_WIND, CHAT_RAIN):
            kind = "weather"

        if pending == CHAT_PICK_YOUR:
            st.session_state["awaiting_chat_location"] = False
            topic = st.session_state.get("chat_topic") or CHAT_TIPS
            reply = _answer_chat_topic(
                topic, "your", results, st.session_state["messages"]
            )
        elif pending == CHAT_PICK_NEAR:
            st.session_state["awaiting_chat_location"] = False
            topic = st.session_state.get("chat_topic") or CHAT_TIPS
            reply = _answer_chat_topic(
                topic, "near", results, st.session_state["messages"]
            )
        elif pending in CHAT_SPARKLES:
            if offer_your and offer_near:
                st.session_state["awaiting_chat_location"] = True
                st.session_state["chat_topic"] = pending
                reply = ask_which_chat_place(results, kind)
            elif offer_near:
                st.session_state["awaiting_chat_location"] = False
                reply = _answer_chat_topic(
                    pending, "near", results, st.session_state["messages"]
                )
            else:
                st.session_state["awaiting_chat_location"] = False
                reply = _answer_chat_topic(
                    pending, "your", results, st.session_state["messages"]
                )
        elif st.session_state.get("awaiting_chat_location"):
            picked = _place_from_text(pending, close)
            if picked == "near" and offer_near:
                st.session_state["awaiting_chat_location"] = False
                topic = st.session_state.get("chat_topic") or CHAT_TIPS
                reply = _answer_chat_topic(
                    topic, "near", results, st.session_state["messages"]
                )
            elif picked == "your" and offer_your:
                st.session_state["awaiting_chat_location"] = False
                topic = st.session_state.get("chat_topic") or CHAT_TIPS
                reply = _answer_chat_topic(
                    topic, "your", results, st.session_state["messages"]
                )
            elif offer_your and offer_near:
                topic = st.session_state.get("chat_topic") or CHAT_TIPS
                kind = "tips"
                if topic in (CHAT_COLD, CHAT_WIND, CHAT_RAIN):
                    kind = "weather"
                reply = ask_which_chat_place(results, kind)
            elif offer_near:
                st.session_state["awaiting_chat_location"] = False
                topic = st.session_state.get("chat_topic") or pending
                reply = _answer_chat_topic(
                    topic, "near", results, st.session_state["messages"]
                )
            else:
                st.session_state["awaiting_chat_location"] = False
                topic = st.session_state.get("chat_topic") or pending
                reply = _answer_chat_topic(
                    topic, "your", results, st.session_state["messages"]
                )
        else:
            reply = agent(st.session_state["messages"])
        st.session_state["messages"].append(
            {"role": "assistant", "content": reply}
        )

    has_user_chat = False
    for msg in st.session_state["messages"]:
        if msg["role"] == "user":
            has_user_chat = True
            break

    with st.expander("✨ Ask about this forecast", expanded=has_user_chat):
        st.markdown(
            "Your midnight picnic menu: **how cold** it will get "
            "(and **what to wear** so you last until the good streak), "
            "whether the **wind** will make itself known, "
            "a **rain** check, or **practical tips for a memorable night**. "
            "Pick a sparkle. 🌟"
        )
        row1a, row1b = st.columns(2)
        if row1a.button("✨ How cold? What to wear?"):
            st.session_state["pending_chat"] = CHAT_COLD
            st.rerun()
        if row1b.button("🌟 Will it be windy?"):
            st.session_state["pending_chat"] = CHAT_WIND
            st.rerun()
        row2a, row2b = st.columns(2)
        if row2a.button("⭐ Will it rain?"):
            st.session_state["pending_chat"] = CHAT_RAIN
            st.rerun()
        if row2b.button("🌠 Practical tips for a memorable night"):
            st.session_state["pending_chat"] = CHAT_TIPS
            st.rerun()

        for msg in st.session_state["messages"]:
            if msg["role"] == "system":
                continue
            avatar = BOT_AVATAR
            if msg["role"] == "user":
                avatar = USER_AVATAR
            st.chat_message(msg["role"], avatar=avatar).write(msg["content"])

        close = results.get("close_location_recommendation")
        if st.session_state.get("awaiting_chat_location"):
            pick1, pick2 = st.columns(2)
            if _offer_your_place(results):
                if pick1.button("Where I will watch from"):
                    st.session_state["pending_chat"] = CHAT_PICK_YOUR
                    st.rerun()
            if _offer_near_you(results) and close:
                if pick2.button("Near you · " + str(close["name"])):
                    st.session_state["pending_chat"] = CHAT_PICK_NEAR
                    st.rerun()

        prompt = st.chat_input("✨ How cold? What to wear? Practical tips?")
        if prompt:
            st.session_state["pending_chat"] = prompt
            st.rerun()
