import streamlit as st

import ui

players = ui.load_players()
result, _ = ui.load_backtest()
best = result["models"][result["best_model"]]["shortlist"]
naive = result["naive_output_baseline"]
latest = int(players.season.max())

st.title("⚽ Moneyball Scout")
st.markdown(
    "#### Find footballers who perform like expensive players but cost a fraction of the price.\n"
    "A model learns how the transfer market prices output, age, playing time, team strength and league "
    "across Europe's Big 5 leagues. Players the model values far above their market price are the "
    "recruitment opportunities. **And the backtest shows the market catches up.**"
)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Player-seasons modelled", f"{len(players):,}", help="Big 5 leagues, 2019/20 to 2025/26, 900+ minutes")
c2.metric("Shortlist value growth vs peers", f"{best['mean_excess_pct']:+.0f}%",
          help="Top-25 budget picks per season vs players of the same season, age band and value quintile, two years later")
c3.metric("Shortlist hit rate", f"{best['hit_rate_pct']:.0f}%", f"vs {naive['hit_rate_pct']:.0f}% naive scout", delta_color="off")
c4.metric("Value model accuracy", "R² 0.85", "out-of-fold, log value", delta_color="off")

st.divider()
st.subheader("How it works")
a, b, c = st.columns(3)
a.markdown("**1 · Data**  \nUnderstat per-90 stats (npxG, xA, xGChain, xGBuildup, shots, key passes) joined to "
           "Transfermarkt market values for 98.8% of player-seasons.")
b.markdown("**2 · Value model**  \nLightGBM predicts each player's market value. Every prediction is out-of-fold, "
           "so no player is valued by a model that has seen him. The gap between model and market is the signal.")
c.markdown("**3 · Proven forward**  \nA walk-forward backtest flags undervalued players using only data available "
           "at the time, then tracks their market value two years later.")

st.divider()
st.subheader(f"Top undervalued players right now ({ui.season_label(latest)}, under €25m, age 24 or under)")
top = players[(players.season == latest) & (players.value_eur <= 25e6) & (players.age <= 24)]
ui.player_table(top.sort_values("value_gap", ascending=False).head(10))
st.caption("Open **Undervalued Board** for filters, **Find Similar** to search by player profile, "
           "and **Scouting Report** for an AI-written report on any player.")
