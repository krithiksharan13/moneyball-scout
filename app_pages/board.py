import numpy as np
import plotly.express as px
import streamlit as st

import ui

players = ui.load_players()
seasons = sorted(players.season.unique(), reverse=True)

st.title("💎 Undervalued Board")
st.caption("Players ranked by how far the model's value exceeds their market value.")

with st.container(border=True):
    f1, f2, f3 = st.columns(3)
    season = f1.selectbox("Season", seasons, format_func=ui.season_label)
    max_value = f2.select_slider("Max market value", options=[2e6, 5e6, 10e6, 15e6, 25e6, 40e6, 60e6, 100e6, 250e6],
                                 value=25e6, format_func=ui.eur)
    max_age = f3.slider("Max age", 17, 36, 26)
    f4, f5, f6 = st.columns(3)
    positions = f4.multiselect("Positions", sorted(players.position.dropna().unique()))
    leagues = f5.multiselect("Leagues", list(ui.LEAGUES.values()))
    min_output = f6.slider("Min output percentile", 0, 90, 0, step=5,
                           help="Require real production. The backtest shows this trades some value growth "
                                "for quality: see the Backtest page.")

pool = players[(players.season == season) & (players.value_eur <= max_value) & (players.age <= max_age)
                & (players.output_pct >= min_output)]
if positions:
    pool = pool[pool.position.isin(positions)]
if leagues:
    pool = pool[pool.league.isin(leagues)]
board = pool.sort_values("value_gap", ascending=False)

st.subheader(f"{len(board)} players match")
ui.player_table(board.head(50))

if len(board):
    st.subheader("Market value vs model value")
    st.caption("Each dot is a player. Above the line, the model values him higher than the market does.")
    fig = px.scatter(board, x="value_eur", y="pred_value_eur", color="position", log_x=True, log_y=True,
                     hover_name="tm_name", hover_data={"team": True, "age": ":.1f", "value_eur": ":,.0f",
                                                       "pred_value_eur": ":,.0f", "position": False},
                     labels={"value_eur": "Market value (€)", "pred_value_eur": "Model value (€)", "position": "Position"})
    lo, hi = board[["value_eur", "pred_value_eur"]].min().min(), board[["value_eur", "pred_value_eur"]].max().max()
    fig.add_shape(type="line", x0=lo, y0=lo, x1=hi, y1=hi, line=dict(color=ui.MUTED, dash="dash"))
    for r in board.head(8).itertuples():
        fig.add_annotation(x=np.log10(r.value_eur), y=np.log10(r.pred_value_eur), text=r.tm_name,
                           showarrow=False, yshift=10, font=dict(size=11))
    fig.update_layout(height=520, margin=dict(t=20))
    st.plotly_chart(fig, width="stretch")
