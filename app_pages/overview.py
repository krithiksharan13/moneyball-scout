import streamlit as st

import components as c
import ui

players = ui.load_players()
result, _ = ui.load_backtest()
best = result["models"][result["best_model"]]["shortlist"]
naive = result["naive_output_baseline"]
latest = int(players.season.max())

st.html("""<div class="mb-hero">
<div class="eyebrow">Big 5 leagues · 2019/20 to 2025/26</div>
<h1>Find players who perform like stars but cost a fraction of the price.</h1>
<p>A model learns how the transfer market prices output, age, playing time and club level. Players it values far
above their market price are recruitment opportunities, and the backtest shows the market tends to catch up.</p>
</div>""")

c.kpis([
    {"label": "Value growth of our picks", "value": f"{best['mean_excess_pct']:+.0f}%", "accent": True,
     "note": "vs similar players over the next 2 years"},
    {"label": "Hit rate", "value": f"{best['hit_rate_pct']:.0f}%",
     "note": f"of picks beat their peers (naive scout: {naive['hit_rate_pct']:.0f}%)"},
    {"label": "Players analysed", "value": f"{len(players):,}", "note": "player-seasons with 900+ minutes"},
    {"label": "Model accuracy", "value": "R² 0.85", "note": "on players it never saw in training"},
])

c.section("How it works")
c.steps([
    ("Join the data", "Understat per-90 stats (expected goals, assists, build-up play) matched to Transfermarkt "
                      "market values for 98.8% of players."),
    ("Price every player", "A LightGBM model predicts each player's market value. The gap between model and "
                           "market is the scouting signal."),
    ("Prove it forward", "Using only data available at the time, we flagged undervalued players each season, "
                         "then tracked their value two years later."),
])

c.section(f"Most undervalued right now · {ui.season_label(latest)}",
          "Under €25m and aged 24 or under. Open the Undervalued Board to change the filters.")
c.card_legend()
top = players[(players.season == latest) & (players.value_eur <= 25e6) & (players.age <= 24)]
c.player_cards(top.sort_values("value_gap", ascending=False).head(6))
