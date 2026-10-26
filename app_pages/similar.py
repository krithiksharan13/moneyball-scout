import streamlit as st

import scout
import ui

players = ui.load_players()
seasons = sorted(players.season.unique(), reverse=True)

st.title("🔍 Find Similar")
st.caption("Pick a player you can't afford. Find statistically similar players you can.")

with st.container(border=True):
    c1, c2 = st.columns([1, 2])
    season = c1.selectbox("Season", seasons, format_func=ui.season_label)
    with c2:
        target = ui.player_picker(players, season, key="similar_player", default_name="Bukayo Saka")
    f1, f2, f3 = st.columns(3)
    max_value = f1.select_slider("Max market value", options=[5e6, 10e6, 15e6, 25e6, 40e6, 60e6, 100e6, 250e6],
                                 value=40e6, format_func=ui.eur)
    max_age = f2.slider("Max age", 17, 36, 27)
    same_position = f3.toggle("Same position only", value=True)

if target.position_group in ("CB", "FB"):
    st.info("Understat has no defensive actions (tackles, interceptions, aerials), so defenders are matched on "
            "ball progression and attacking involvement only.")

st.markdown(f"**{target.tm_name}** · {target.team} · {target.position} · age {target.age:.0f} · "
            f"market {ui.eur(target.value_eur)} · model {ui.eur(target.pred_value_eur)}")

matches = scout.similar_players(players, int(target.player_id), season, n=15, max_value=max_value,
                                max_age=max_age, same_position=same_position)
if matches.empty:
    st.warning("No players match these filters. Try raising the value or age limit.")
    st.stop()

ui.player_table(matches, extra={"similarity": st.column_config.ProgressColumn(
    "Similarity", min_value=0, max_value=1, format="%.2f")})

st.subheader("Profile comparison")
st.caption("Percentiles vs the same position group and season.")
compare = st.selectbox("Compare with", range(len(matches)), format_func=lambda i: matches.iloc[i].tm_name)
left, right = st.columns([3, 2])
pick = matches.iloc[compare]
left.plotly_chart(ui.radar([target, pick], [target.tm_name, pick.tm_name]), width="stretch")
with right:
    st.metric(f"{pick.tm_name} market value", ui.eur(pick.value_eur),
              f"{ui.eur(target.value_eur - pick.value_eur)} cheaper than {target.tm_name}", delta_color="off")
    st.metric("Model value", ui.eur(pick.pred_value_eur), f"{(pick.gap_ratio - 1) * 100:+.0f}% vs market")
    if st.button(f"Write a scouting report on {pick.tm_name}", type="primary"):
        st.session_state["player_id"] = int(pick.player_id)
        st.session_state["report_season"] = season
        st.switch_page("app_pages/player_report.py")
