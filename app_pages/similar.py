import streamlit as st

import components as c
import scout
import ui
from fmt import eur

players = ui.load_players()
seasons = sorted(players.season.unique(), reverse=True)

c.page_title("🔍 Find Similar", "Pick a player you can't afford. Find statistically similar players you can.")

with st.container(border=True):
    st.html('<span class="filters-anchor"></span>')
    f1, f2 = st.columns([1, 3])
    season = f1.selectbox("Season", seasons, format_func=ui.season_label)
    with f2:
        target = ui.player_picker(players, season, key="similar_player", default_name="Bukayo Saka")
    f3, f4, f5 = st.columns(3)
    max_value = f3.select_slider("Max market value", options=[2e6, 5e6, 10e6, 15e6, 25e6, 40e6, 60e6, 100e6, 250e6],
                                 value=40e6, format_func=eur)
    max_age = f4.slider("Max age", 17, 36, 27)
    same_position = f5.toggle("Same position only", value=True)

c.section(f"Players like {target.tm_name}",
          f"{target.team} · {target.position} · age {target.age:.0f} · market {eur(target.value_eur)} · "
          f"model {eur(target.pred_value_eur)}")
if target.position_group in ("CB", "FB"):
    st.info("Understat has no defensive actions (tackles, interceptions, aerials), so defenders are matched on "
            "ball progression and attacking involvement only.")

matches = scout.similar_players(players, int(target.player_id), season, n=12, max_value=max_value,
                                max_age=max_age, same_position=same_position)
if matches.empty:
    st.warning("No players match these filters. Try raising the value or age limit.")
    st.stop()

c.card_legend()
c.player_cards(matches, extra_chip="similarity")

c.section("Side-by-side profile", "Percentiles vs the same position group and season. Further out = better.")
names = dict(zip(matches.player_id, matches.tm_name))
pick_id = st.selectbox("Compare with", list(names), format_func=names.get)
pick = matches[matches.player_id == pick_id].iloc[0]
left, right = st.columns([3, 2])
left.plotly_chart(ui.radar([target, pick], [target.tm_name, pick.tm_name]), width="stretch", theme=None)
with right:
    saving = target.value_eur - pick.value_eur
    c.kpis([
        {"label": pick.tm_name, "value": eur(pick.value_eur), "accent": True,
         "note": (f"{eur(saving)} cheaper than {target.tm_name}" if saving > 0 else
                  f"{eur(-saving)} more than {target.tm_name}")},
        {"label": "Similarity", "value": f"{pick.similarity * 100:.0f}%",
         "note": f"Model value {eur(pick.pred_value_eur)} ({(pick.gap_ratio - 1) * 100:+.0f}% vs market)"},
    ])
    if st.button(f"📝 Scouting report on {pick.tm_name}", type="primary", width="stretch"):
        st.session_state["player_id"] = int(pick.player_id)
        st.session_state["report_season"] = int(season)
        st.switch_page("app_pages/player_report.py")
