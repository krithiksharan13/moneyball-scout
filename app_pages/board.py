import numpy as np
import plotly.graph_objects as go
import streamlit as st

import components as c
import theme
import ui
from fmt import eur, log_ticks, ordinal

PAGE = 12
players = ui.load_players()
seasons = sorted(players.season.unique(), reverse=True)

c.page_title("💎 Undervalued Board", "Players ranked by how far the model's value is above their market value.")

with st.container(border=True):
    st.html('<span class="filters-anchor"></span>')
    f1, f2, f3, f4 = st.columns(4)
    season = f1.selectbox("Season", seasons, format_func=ui.season_label)
    max_value = f2.select_slider("Max market value", options=[1e6, 2e6, 5e6, 10e6, 15e6, 25e6, 40e6, 60e6, 100e6, 250e6],
                                 value=25e6, format_func=eur)
    max_age = f3.slider("Max age", 17, 36, 26)
    min_output = f4.slider("Min output percentile", 0, 90, 0, step=5,
                           help="Require real production. The backtest shows this trades some value growth for "
                                "quality: see the Backtest page.")
    f5, f6, f7 = st.columns([2, 2, 1.3])
    positions = f5.multiselect("Positions", sorted(players.position.dropna().unique()), placeholder="All positions")
    leagues = f6.multiselect("Leagues", list(ui.LEAGUES.values()), placeholder="All leagues")
    sort = f7.selectbox("Sort by", ["Biggest gap", "Highest output", "Cheapest", "Youngest"])

pool = players[(players.season == season) & (players.value_eur <= max_value) & (players.age <= max_age)
               & (players.output_pct >= min_output)]
if positions:
    pool = pool[pool.position.isin(positions)]
if leagues:
    pool = pool[pool.league.isin(leagues)]
order = {"Biggest gap": ("value_gap", False), "Highest output": ("output_pct", False),
         "Cheapest": ("value_eur", True), "Youngest": ("age", True)}[sort]
board = pool.sort_values(order[0], ascending=order[1]).reset_index(drop=True)

# Reset paging whenever the filters change.
signature = (season, max_value, max_age, min_output, tuple(positions), tuple(leagues), sort)
if st.session_state.get("board_sig") != signature:
    st.session_state["board_sig"] = signature
    st.session_state["board_n"] = PAGE

c.section(f"{len(board)} players match")
if board.empty:
    st.info("No players match these filters. Try a higher value limit or a lower output percentile.")
    st.stop()

cards, chart, table = st.tabs(["🃏 Cards", "📊 Chart", "📋 Table"])

with cards:
    c.card_legend()
    n = st.session_state["board_n"]
    c.player_cards(board.head(n))
    if n < len(board):
        if st.button(f"Show more ({len(board) - n} left)", width="stretch"):
            st.session_state["board_n"] = n + PAGE
            st.rerun()

with chart:
    st.caption("Each dot is a player. Above the dashed line, the model values him higher than the market does. "
               "Hover for details.")
    fig = go.Figure()
    for line, color in zip(["Attack", "Midfield", "Defence"], [theme.t("s1"), theme.t("s2"), theme.t("s3")]):
        d = board[board.line == line]
        fig.add_trace(go.Scatter(
            x=d.value_eur, y=d.pred_value_eur, mode="markers", name=line,
            marker=dict(size=9, color=color, opacity=0.8, line=dict(width=1, color=theme.t("surface"))),
            customdata=np.stack([d.tm_name, d.team, d.position, d.age.round(0), d.value_eur.map(eur),
                                 d.pred_value_eur.map(eur), d.output_pct.map(ordinal)], axis=-1) if len(d) else None,
            hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[1]} · %{customdata[2]} · age %{customdata[3]}"
                          "<br>Market %{customdata[4]} → Model %{customdata[5]}<br>Output %{customdata[6]} pct<extra></extra>"))
    lo = board[["value_eur", "pred_value_eur"]].min().min()
    hi = board[["value_eur", "pred_value_eur"]].max().max()
    fig.add_trace(go.Scatter(x=[lo, hi], y=[lo, hi], mode="lines", showlegend=False, hoverinfo="skip",
                             line=dict(color=theme.t("muted"), dash="dash", width=1.5)))
    top5 = board.head(5)
    fig.add_trace(go.Scatter(
        x=top5.value_eur, y=top5.pred_value_eur, mode="markers", name="Top 5 on the board", hoverinfo="skip",
        marker=dict(size=18, color="rgba(0,0,0,0)", line=dict(width=2.5, color=theme.t("ink")))))
    tv, tt = log_ticks(lo, hi)
    theme.style_fig(fig, height=540)
    fig.update_layout(margin=dict(l=70, r=10, t=20, b=10))
    fig.update_xaxes(type="log", title="Market value", tickvals=tv, ticktext=tt)
    fig.update_yaxes(type="log", title="Model value", tickvals=tv, ticktext=tt)
    st.plotly_chart(fig, width="stretch", theme=None)

with table:
    c.table(board.head(100), {
        "tm_name": ("Player", str), "team": ("Team", str), "league": ("League", str), "position": ("Position", str),
        "age": ("Age", lambda v: f"{v:.0f}"), "value_eur": ("Market", eur), "pred_value_eur": ("Model", eur),
        "gap_ratio": ("Model vs market", lambda v: f"{(v - 1) * 100:+.0f}%"),
        "output_pct": ("Output pct", lambda v: ordinal(v)),
    }, numeric={"age", "value_eur", "pred_value_eur", "gap_ratio", "output_pct"})
    csv = board[["tm_name", "team", "league", "position", "age", "minutes", "value_eur", "pred_value_eur",
                 "gap_ratio", "output_pct"]].round(2).to_csv(index=False).encode("utf-8")
    st.download_button("Download shortlist (CSV)", csv, file_name=f"moneyball_shortlist_{season}.csv", mime="text/csv")
