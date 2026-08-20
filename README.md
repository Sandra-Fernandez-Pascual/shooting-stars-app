# Shooting Stars Bot

An English-language Streamlit app that answers: **when should I go outside to watch shooting stars from this city?**

You pick a city, a date in the next 14 days, and how dark your sky is. In a big city you can also say which side you are on. Python estimates the best viewing window. Grok only explains those numbers in a chat about clothing and comfort.

## Features

- City lookup and 14-day hourly weather from Open-Meteo
- Astronomical night only (Sun more than 18 degrees below the horizon)
- Local meteor-shower catalog in `data/showers.json`
- Visible meteor estimate, then the best 1–3 hour block
- Score from 0–100 compared with the other nights in the forecast
- Two other nights, a nearby darker place, and other sides of a big city
- Chat for how cold it will feel, wind, rain, and practical tips for that window
- Grok chat (`grok-3-mini`) that must not invent numbers

## How the estimate works

Python looks at every astronomical-night hour:

`R_h = ZHR_h * sin(radiant_altitude) * r^(LM_h - 6.5) * (1 - cloud_cover / 100)`

- **ZHR** is shower activity (Gaussian around the peak date)
- **Radiant** is the point meteors appear to come from
- **LM** is sky darkness (your sky-quality choice plus moonlight)
- **Cloud cover** comes from the forecast

The recommended time is the three consecutive hours with the highest sum of `R_h`.

The score is:

`score = 100 * this_window / best_window_in_the_14_days`

The best night in the forecast gets 100.

Where you will watch from (brighter places hide more meteors):

- Countryside → Bortle 2, LM about 7.0
- Village or suburb → Bortle 4, LM about 6.0
- Residential street → Bortle 6, LM about 5.0
- City centre → Bortle 8, LM about 4.0

A **viewing night** runs from local noon on the selected date to local noon the next day. So 02:00–05:00 on 13 August still belongs to the night of 12 August.

## Setup

### 1. Clone and install

```bash
cd shooting-stars-app
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. API key

Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and add your xAI key:

```toml
XAI_API_KEY = "xai-your-key-here"
```

`.streamlit/secrets.toml` is gitignored. Get a key at [console.x.ai](https://console.x.ai/). The viewing forecast still works without a key; only chat needs it.

### 3. Run the app

```bash
streamlit run app.py
```

Open the URL Streamlit prints (usually `http://localhost:8501`).

The first forecast can take about 30–60 seconds while Python computes Sun, Moon, and radiant positions for each night hour. Streamlit shows a spinner during that time.

## Project layout

```
shooting-stars-app/
  app.py                 # Streamlit app
  ai/agent.py            # Grok chat only
  ai/prompts.py          # system prompt, result text, practical tips
  ai/tools.py            # weather, astronomy, visibility, scoring
  ai/utils.py            # geocoding, sky quality, dates, nearby places
  ai/theme.py            # starry UI
  ai/meteor_schema.py    # load showers.json
  data/showers.json      # major showers
  .streamlit/config.toml # theme colors
  .streamlit/secrets.toml.example  # sample for local secrets
  requirements.txt
  README.md
```

Code style: functions, dictionaries, and pandas. No custom classes.

## Deploy on Streamlit Community Cloud

1. Push this repo to GitHub
2. At [share.streamlit.io](https://share.streamlit.io), create an app
3. Main file: `app.py`
4. In **Secrets**, add:

```
XAI_API_KEY = "xai-your-key-here"
```

No database secrets are needed.

## Known limits

- Radiant coordinates are a peak-night approximation
- Cloud cover 14 days ahead is only a forecast
- Grok must stay inside the numbers Python calculated
- Near the poles, some dates have almost no astronomical night
- Nearby places come from OpenStreetMap; small urban plantings are skipped
