"""Load the meteor-shower catalog from data/showers.json.

Each shower is a dictionary with name, active dates, peak date,
radiant coordinates, ZHR, population index r, and sigma_days.
"""

import json
import os
from datetime import date


SHOWERS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "data",
    "showers.json",
)


def load_showers():
    """Read showers.json and return a list of shower dictionaries.

    Returns:
        list of dict: one dictionary per meteor shower.
    """
    with open(SHOWERS_PATH, encoding="utf-8") as file:
        showers = json.load(file)
    return showers


def _month_day(text):
    """Turn a 'MM-DD' string into (month, day) integers.

    Args:
        text (str): month and day, for example '08-12'.

    Returns:
        tuple: (month, day)
    """
    month_text, day_text = text.split("-")
    return int(month_text), int(day_text)


def shower_peak_on_year(shower, year):
    """Build the peak calendar date of a shower for a given year.

    Args:
        shower (dict): one shower from the catalog.
        year (int): the year to use.

    Returns:
        datetime.date: peak date in that year.
    """
    month, day = _month_day(shower["peak_date"])
    return date(year, month, day)


def is_active(shower, check_date):
    """Return True if the shower is active on check_date.

    Handles showers that wrap around New Year (for example Quadrantids).

    Args:
        shower (dict): one shower from the catalog.
        check_date (datetime.date): the night we care about.

    Returns:
        bool: True if the date falls inside the active period.
    """
    start_month, start_day = _month_day(shower["active_start"])
    end_month, end_day = _month_day(shower["active_end"])
    year = check_date.year

    start = date(year, start_month, start_day)
    end = date(year, end_month, end_day)

    # Normal showers stay inside one calendar year (Perseids: Jul-Aug).
    if start <= end:
        return start <= check_date <= end

    # Year-wrap showers (Quadrantids: 28 Dec to 12 Jan).
    # The active window is late this year OR early this year.
    start_this_year = date(year, start_month, start_day)
    end_this_year = date(year, end_month, end_day)
    return check_date >= start_this_year or check_date <= end_this_year


def days_from_peak(shower, check_date):
    """How many days check_date is from the nearest peak date.

    For year-wrap showers we compare against last year's peak too,
    so 31 December is close to 3 January.

    Args:
        shower (dict): one shower from the catalog.
        check_date (datetime.date): the night we care about.

    Returns:
        int: signed number of days (negative = before the peak).
    """
    year = check_date.year
    peak_this_year = shower_peak_on_year(shower, year)
    peak_last_year = shower_peak_on_year(shower, year - 1)
    peak_next_year = shower_peak_on_year(shower, year + 1)

    diff_this = (check_date - peak_this_year).days
    diff_last = (check_date - peak_last_year).days
    diff_next = (check_date - peak_next_year).days

    # Pick the peak that is closest in time.
    candidates = [diff_this, diff_last, diff_next]
    closest = candidates[0]
    for diff in candidates:
        if abs(diff) < abs(closest):
            closest = diff
    return closest


def find_active_shower(showers, check_date):
    """Pick the strongest shower that is active on check_date.

    If two showers overlap, we keep the one with the higher peak ZHR.

    Args:
        showers (list): catalog from load_showers().
        check_date (datetime.date): the night we care about.

    Returns:
        dict or None: the chosen shower, or None if none is active.
    """
    active = []
    for shower in showers:
        if is_active(shower, check_date):
            active.append(shower)

    if len(active) == 0:
        return None

    best = active[0]
    for shower in active:
        if shower["zhr_peak"] > best["zhr_peak"]:
            best = shower
    return best
