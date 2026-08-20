"""Starry UI: colors, chat avatars, and the official Coldplay player."""

import streamlit as st
import streamlit.components.v1 as components

BOT_AVATAR = "✨"
USER_AVATAR = "🌙"

# Official Coldplay video on YouTube — not a copied audio file.
# Loop + a sticky parent-page player: Streamlit reruns kill in-page embeds.
YOUTUBE_VIDEO = "VPRjCeoBqrI"

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
  padding-bottom: 7rem;
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

.soundtrack-label {
  font-family: "Cormorant Garamond", serif;
  font-size: 1.15rem;
  color: #e8c547;
  margin-bottom: 0.15rem;
}

@media (prefers-color-scheme: light) {
  .stApp, [data-testid="stAppViewContainer"] {
    background:
      radial-gradient(1000px 600px at 50% -15%, #b9c8f0 0%, transparent 55%),
      linear-gradient(180deg, #d7e2f8 0%, #eef2fb 45%, #f7f4ea 100%);
  }
  .stApp, [data-testid="stCaptionContainer"] {
    color: #152047;
  }
  h1, h2, h3 {
    color: #152047 !important;
  }
  [data-testid="stWidgetLabel"],
  [data-testid="stWidgetLabel"] *,
  [data-testid="stCaptionContainer"],
  [data-testid="stCaptionContainer"] *,
  [data-testid="stTextInput"] label,
  [data-testid="stDateInput"] label,
  [data-testid="stSelectbox"] label,
  [data-testid="stSelectbox"] p {
    color: #152047 !important;
  }
  [data-testid="stTextInput"] input,
  [data-testid="stDateInput"] input,
  [data-baseweb="select"] > div,
  [data-baseweb="select"] span {
    background-color: #ffffff !important;
    color: #152047 !important;
  }
  [data-testid="stTextInput"] input::placeholder {
    color: #5a6a90 !important;
  }
  .starfield span {
    background: #fff;
    box-shadow: 0 0 4px #fff;
  }
  .stButton > button {
    background: linear-gradient(180deg, #ffffff 0%, #e8eefc 100%);
    color: #152047;
    border-color: rgba(21, 32, 71, 0.18);
  }
  .stButton > button[kind="primary"] {
    background: linear-gradient(180deg, #e8c547 0%, #c9a227 100%);
    color: #1a1430;
  }
  [data-testid="stExpander"],
  [data-testid="stChatMessage"] {
    background: rgba(255, 255, 255, 0.88);
    border-color: rgba(21, 32, 71, 0.12);
  }
  [data-testid="stChatMessage"],
  [data-testid="stChatMessage"] p,
  [data-testid="stChatMessage"] li,
  [data-testid="stChatMessage"] span,
  [data-testid="stExpander"] [data-testid="stMarkdownContainer"] p {
    color: #152047 !important;
  }
  .near-you {
    background: #151b3a;
    color: #e8eefc;
  }
  .sky-metric {
    background: #ffffff;
    border: 1px solid #152047;
  }
  .sky-metric-label {
    color: #6b4e00 !important;
  }
  .sky-metric-value {
    color: #152047 !important;
  }
  .soundtrack-label {
    color: #6b4e00;
  }
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
    """Paint the night sky behind the app. Follows light/dark system colors."""
    st.markdown(STARRY_CSS, unsafe_allow_html=True)
    st.markdown(
        '<div class="starfield">'
        + _star_dots()
        + '<div class="shooting-star"></div></div>',
        unsafe_allow_html=True,
    )


def soundtrack_player():
    """Official YouTube player that stays put, loops, and starts itself.

    Browsers block sound until the page is used. The first click or key
    anywhere on the app starts the song; Streamlit reruns do not stop it.
    """
    components.html(_soundtrack_bootstrap(), height=1)


def _soundtrack_bootstrap():
    """Mount a looping player on the parent page and start it on first use."""
    html = r"""
<script>
(function () {
  var doc = window.parent && window.parent.document
    ? window.parent.document
    : document;
  var old = doc.getElementById("sky-soundtrack");
  if (old && old.getAttribute("data-sky") === "v4") {
    return;
  }
  if (old) {
    old.remove();
  }

  var style = doc.getElementById("sky-soundtrack-style");
  if (!style) {
    style = doc.createElement("style");
    style.id = "sky-soundtrack-style";
    doc.head.appendChild(style);
  }
  style.textContent = [
    "#sky-soundtrack {",
    "  position: fixed; right: 1rem; bottom: 1rem; z-index: 2147483000;",
    "  width: 300px; padding: 0.7rem 0.75rem 0.8rem;",
    "  background: rgba(11, 16, 38, 0.96);",
    "  border: 1px solid rgba(232, 197, 71, 0.45);",
    "  border-radius: 16px;",
    "  box-shadow: 0 10px 30px rgba(5, 8, 20, 0.45);",
    "  font-family: Outfit, sans-serif; color: #e8eefc;",
    "}",
    "#sky-soundtrack .sky-copy { font-size: 0.86rem; line-height: 1.35; margin-top: 0.55rem; }",
    "#sky-soundtrack .sky-copy strong {",
    "  display: block; font-family: 'Cormorant Garamond', serif;",
    "  font-size: 1.08rem; color: #e8c547; margin-bottom: 0.2rem;",
    "}",
    "#sky-soundtrack #sky-yt-host, #sky-soundtrack iframe {",
    "  width: 100%; height: 169px; border: 0; border-radius: 10px;",
    "  background: #000; display: block;",
    "}",
    "@media (max-width: 640px) {",
    "  #sky-soundtrack { left: 0.6rem; right: 0.6rem; bottom: 0.6rem; width: auto; }",
    "}"
  ].join(" ");

  var bar = doc.createElement("div");
  bar.id = "sky-soundtrack";
  bar.setAttribute("data-sky", "v4");
  bar.innerHTML =
    '<div id="sky-yt-host"></div>'
    + '<div class="sky-copy"><strong>A sky full of stars is waiting for you</strong>'
    + "Let yourself go with the music while planning your dreamy night away.</div>";
  doc.body.appendChild(bar);

  if (doc.getElementById("sky-player-boot")) {
    return;
  }
  var boot = doc.createElement("script");
  boot.id = "sky-player-boot";
  boot.textContent = [
    "(function(){",
    "  var videoId = 'VIDEO_ID';",
    "  function tryPlay() {",
    "    try {",
    "      if (window.skyPlayer && window.skyPlayer.playVideo) {",
    "        window.skyPlayer.unMute();",
    "        window.skyPlayer.playVideo();",
    "      }",
    "    } catch (err) {}",
    "  }",
    "  function startPlayer() {",
    "    if (!window.YT || !window.YT.Player) { return; }",
    "    if (window.skyPlayer) { tryPlay(); return; }",
    "    window.skyPlayer = new window.YT.Player('sky-yt-host', {",
    "      height: '169', width: '300', videoId: videoId,",
    "      playerVars: { autoplay: 1, mute: 0, loop: 1, playlist: videoId,",
    "        rel: 0, modestbranding: 1, playsinline: 1 },",
    "      events: {",
    "        onReady: function(e) { e.target.unMute(); e.target.playVideo(); },",
    "        onStateChange: function(e) {",
    "          if (e.data === window.YT.PlayerState.ENDED) { e.target.playVideo(); }",
    "        }",
    "      }",
    "    });",
    "  }",
    "  document.addEventListener('pointerdown', tryPlay, true);",
    "  document.addEventListener('keydown', tryPlay, true);",
    "  window.onYouTubeIframeAPIReady = startPlayer;",
    "  if (window.YT && window.YT.Player) { startPlayer(); }",
    "  else {",
    "    var tag = document.createElement('script');",
    "    tag.src = 'https://www.youtube.com/iframe_api';",
    "    document.head.appendChild(tag);",
    "  }",
    "})();"
  ].join("");
  doc.body.appendChild(boot);
})();
</script>
"""
    return html.replace("VIDEO_ID", YOUTUBE_VIDEO)

