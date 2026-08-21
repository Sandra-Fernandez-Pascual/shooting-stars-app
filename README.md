# Shooting Stars Bot

A little night-sky companion that finds the best hour to watch shooting stars from where you are — then helps you get cozy for the show.

[![Live App](https://img.shields.io/badge/Live_App-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://shooting-stars.streamlit.app/)
[![Project Planning](https://img.shields.io/badge/Project_Planning-0052CC?style=for-the-badge&logo=trello&logoColor=white)](https://trello.com/b/hWIYxGgN/shooting-stars-bot)
[![Final Presentation](https://img.shields.io/badge/Final_Presentation-00C4CC?style=for-the-badge&logo=canva&logoColor=white)](https://www.canva.com/design/DAHS6aFI8Kg/yypa5wGGLWUUzkMcDAlNQg/view)

## How to use it

Open the [live app](https://shooting-stars.streamlit.app/), then:

1. Enter a city.
2. Pick a date in the next 14 days.
3. Say where will you watch from. In a big city, you can also pick a side of town.
4. Click **Find best viewing time**.
5. Read your forecast: best hour, estimated meteors, other nights, and darker spots nearby.
6. Ask the chat about clothing, wind, rain, or practical tips for that night.

## Features

- City lookup and 14-day hourly weather from Open-Meteo
- Astronomical night only (Sun more than 18 degrees below the horizon)
- Local meteor-shower catalog in `data/showers.json`
- Visible meteor estimate, then the best 1–3 hour block
- Score from 0–100 compared with the other nights in the forecast
- Two other nights, a nearby darker place, and other sides of a big city
- Chat for how cold it will feel, wind, rain, and practical tips for that window
- Grok chat (`grok-3-mini`)

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

Code style: functions, dictionaries and pandas.
