"""Starry UI: colors and chat avatars."""

import streamlit as st
import streamlit.components.v1 as components

BOT_AVATAR = "✨"
USER_AVATAR = "🌙"

STARRY_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,600;1,500&family=Outfit:wght@400;500;600&display=swap');

html, body, [data-testid="stAppViewContainer"], .stApp {
  font-family: "Outfit", sans-serif;
}

h1, h2, h3, [data-testid="stMarkdownContainer"] h1 {
  font-family: "Cormorant Garamond", serif !important;
  letter-spacing: 0.02em;
}

header[data-testid="stHeader"] {
  background: transparent;
}

.block-container {
  padding-top: 1.4rem;
  padding-bottom: 3rem;
  max-width: 46rem;
}

.starfield {
  pointer-events: none;
  position: fixed;
  inset: 0;
  z-index: 0;
  overflow: hidden;
}

.starfield span {
  position: absolute;
  width: 2px;
  height: 2px;
  border-radius: 50%;
  background: #fff;
  opacity: 0.7;
  animation: twinkle 4.8s ease-in-out infinite;
}

.shooting-star {
  position: absolute;
  top: 8%;
  left: -10%;
  width: 90px;
  height: 2px;
  background: linear-gradient(90deg, transparent, #fff6c8, transparent);
  opacity: 0;
  transform: rotate(18deg);
  animation: shoot 11s ease-in-out infinite;
}

@keyframes twinkle {
  0%, 100% { opacity: 0.25; transform: scale(0.8); }
  50% { opacity: 0.95; transform: scale(1.2); }
}

@keyframes shoot {
  0% { transform: translate(0, 0) rotate(18deg); opacity: 0; }
  8% { opacity: 0.9; }
  28% { transform: translate(85vw, 28vh) rotate(18deg); opacity: 0; }
  100% { transform: translate(85vw, 28vh) rotate(18deg); opacity: 0; }
}

.stApp, [data-testid="stAppViewContainer"] {
  background:
    radial-gradient(1200px 700px at 50% -10%, #24315c 0%, transparent 55%),
    radial-gradient(900px 500px at 100% 100%, #1a1640 0%, transparent 50%),
    #0b1026;
}

[data-testid="stAppViewContainer"] > .main {
  position: relative;
  z-index: 1;
}

.stButton > button {
  border-radius: 999px;
  border: 1px solid rgba(232, 197, 71, 0.45);
  background: linear-gradient(180deg, #1e2a55 0%, #151b3a 100%);
  color: #f4efe2;
  font-weight: 500;
  min-height: 2.7rem;
}

.stButton > button:hover {
  border-color: #e8c547;
  box-shadow: 0 0 16px rgba(232, 197, 71, 0.28);
}

.stButton > button[kind="primary"] {
  background: linear-gradient(180deg, #e8c547 0%, #c9a227 100%);
  color: #1a1430;
  border: none;
  font-weight: 600;
}

div[data-testid="stMetric"] {
  background: #1a2748 !important;
  border: 1px solid #e8c547;
  border-radius: 16px;
  padding: 0.75rem 0.9rem;
}

.sky-metrics {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 0.8rem;
  margin: 0.5rem 0 1rem;
}
.sky-metric {
  background: #1a2748;
  border: 1px solid #e8c547;
  border-radius: 16px;
  padding: 0.95rem 1rem 1rem;
}
.sky-metric-label,
.sky-metric-value {
  margin: 0 !important;
}
.sky-metric-label {
  color: #e8c547 !important;
  font-family: "Outfit", sans-serif !important;
  font-size: 0.92rem !important;
  font-weight: 500 !important;
  letter-spacing: 0.02em;
  line-height: 1.3 !important;
}
.sky-metric-value {
  color: #ffffff !important;
  font-family: "Cormorant Garamond", serif !important;
  font-size: 1.55rem !important;
  font-weight: 600 !important;
  line-height: 1.25 !important;
  margin-top: 0.3rem !important;
  letter-spacing: 0.02em;
}

.near-you {
  background: #151b3a;
  border: 1px solid rgba(232, 197, 71, 0.45);
  border-radius: 16px;
  padding: 0.9rem 1.05rem;
  color: #e8eefc !important;
  margin: 0.4rem 0 0.8rem;
}
.near-you, .near-you * {
  color: #e8eefc !important;
}
.near-you strong {
  color: #e8c547 !important;
  font-family: "Cormorant Garamond", serif;
  font-size: 1.2rem;
}

[data-testid="stExpander"] {
  background: rgba(11, 16, 38, 0.55);
  border: 1px solid rgba(232, 197, 71, 0.22);
  border-radius: 18px;
}

[data-testid="stChatMessage"] {
  background: rgba(21, 27, 58, 0.55);
  border-radius: 16px;
  border: 1px solid rgba(155, 180, 255, 0.12);
}

@media (max-width: 640px) {
  .block-container {
    padding-left: 0.85rem;
    padding-right: 0.85rem;
    padding-top: 0.8rem;
  }
  h1 { font-size: 2rem !important; }
  .sky-metrics {
    grid-template-columns: 1fr;
  }
  [data-testid="stHorizontalBlock"] {
    flex-wrap: wrap;
    gap: 0.5rem;
  }
  [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
    min-width: 100% !important;
    flex: 1 1 100% !important;
  }
  .stButton > button {
    width: 100%;
    min-height: 2.9rem;
  }
}
</style>
"""


def _star_dots():
    """A handful of CSS stars at fixed positions."""
    spots = [
        (8, 12, 0), (22, 28, 1.1), (41, 9, 0.4), (63, 18, 1.8),
        (81, 7, 0.7), (91, 32, 2.2), (14, 44, 1.4), (35, 61, 0.2),
        (58, 48, 2.6), (77, 70, 0.9), (5, 78, 1.7), (48, 22, 3.1),
        (70, 40, 0.3), (88, 58, 2.0), (28, 86, 1.2), (52, 80, 2.4),
    ]
    bits = []
    for left, top, delay in spots:
        bits.append(
            '<span style="left:'
            + str(left)
            + "%;top:"
            + str(top)
            + "%;animation-delay:"
            + str(delay)
            + 's;"></span>'
        )
    return "".join(bits)


def apply_starry_theme():
    """Paint the night sky behind the app. Always uses the dark theme."""
    st.markdown(STARRY_CSS, unsafe_allow_html=True)
    st.markdown(
        '<div class="starfield">'
        + _star_dots()
        + '<div class="shooting-star"></div></div>',
        unsafe_allow_html=True,
    )
    components.html(
        """
<script>
(function () {
  var doc = window.parent && window.parent.document
    ? window.parent.document
    : document;
  var ids = ["sky-soundtrack", "sky-soundtrack-style", "sky-player-boot"];
  var i;
  for (i = 0; i < ids.length; i++) {
    var el = doc.getElementById(ids[i]);
    if (el) {
      el.remove();
    }
  }
})();
</script>
        """,
        height=1,
    )

