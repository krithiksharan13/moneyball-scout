import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import ui

result, rows = ui.load_backtest()
best_name = result["best_model"]
best = result["models"][best_name]
budget = ui.eur(result["budget_eur"])

st.title("📈 Backtest")
st.markdown(
    f"**Does a high value gap actually predict anything?** For each season from {result['flag_seasons'][0]} to "
    f"{result['flag_seasons'][-1]}, the model was trained only on data available at the time. It picked the "
    f"{result['shortlist_size_per_season']} most undervalued players under {budget}, and we tracked their "
    "Transfermarkt value two years later."
)

s = best["shortlist"]
c1, c2, c3 = st.columns(3)
c1.metric("Growth vs comparable players", f"{s['mean_excess_pct']:+.0f}%",
          help="Compared with players of the same season, age band and value quintile")
c2.metric("Hit rate", f"{s['hit_rate_pct']:.0f}%", help="Share of picks whose value grew more than their comparison group")
c3.metric("Picks evaluated", s["n"])

st.subheader("Shortlist vs alternatives")
compare = pd.DataFrame([
    {"Strategy": "Moneyball Scout (market-gap model)", **result["models"]["market"]["shortlist"]},
    {"Strategy": "Performance-only gap model", **result["models"]["performance"]["shortlist"]},
    {"Strategy": "Naive scout: best npxG + xA per 90", **result["naive_output_baseline"]},
    {"Strategy": f"Every player under {budget}", **result["all_budget_players"]},
])
fig = go.Figure(go.Bar(x=compare.mean_excess_pct, y=compare.Strategy, orientation="h",
                       marker_color=[ui.ACCENT, "#86efac", ui.MUTED, "#cbd5e1"],
                       text=[f"{v:+.0f}%" for v in compare.mean_excess_pct], textposition="outside"))
fig.update_layout(height=280, margin=dict(t=10, l=10, r=40), xaxis_title="Value growth vs comparable players (2 years)",
                  yaxis=dict(autorange="reversed"))
st.plotly_chart(fig, width="stretch")

st.subheader("The bigger the gap, the bigger the growth")
st.caption("All players, split into ten equal groups by value gap within each season (1 = most overvalued, 10 = most undervalued).")
deciles = best["decile_excess_pct"]
fig = go.Figure(go.Bar(x=[f"D{k}" for k in deciles], y=list(deciles.values()),
                       marker_color=[ui.ACCENT if v > 0 else "#ef4444" for v in deciles.values()],
                       text=[f"{v:+.0f}%" for v in deciles.values()], textposition="outside"))
fig.update_layout(height=360, margin=dict(t=10), yaxis_title="Value growth vs comparable players")
st.plotly_chart(fig, width="stretch")

st.subheader("Consistent across seasons")
by = pd.DataFrame(best["by_season"]).T
by.index = [ui.season_label(int(i)) for i in by.index]
st.dataframe(by.rename(columns={"n": "Picks", "median_value_change_pct": "Median raw value change %",
                                "mean_excess_pct": "Growth vs peers %", "hit_rate_pct": "Hit rate %"}),
             width="stretch")

st.subheader("Value growth vs production: the trade-off")
st.caption("Same shortlist, but only picking players above a minimum output percentile. The market re-prices youth "
           "and playing time more than production, so demanding output costs some growth but still beats the naive scout.")
sens = result["output_filter_sensitivity"]
fig = go.Figure(go.Bar(x=[f"≥ {k}th pct" if k != "0" else "No filter" for k in sens],
                       y=[v["mean_excess_pct"] for v in sens.values()], marker_color=ui.ACCENT,
                       text=[f"{v['mean_excess_pct']:+.0f}% · hit {v['hit_rate_pct']:.0f}%" for v in sens.values()],
                       textposition="outside"))
fig.add_hline(y=result["naive_output_baseline"]["mean_excess_pct"], line_dash="dash", line_color=ui.MUTED,
              annotation_text="Naive scout", annotation_position="top left")
fig.update_layout(height=340, margin=dict(t=20), yaxis_title="Value growth vs comparable players",
                  xaxis_title="Minimum output percentile")
st.plotly_chart(fig, width="stretch")

st.subheader("Biggest hits")
hits = pd.DataFrame(result["example_picks"]).head(15)
hits["Value then"] = hits.value_eur.map(ui.eur)
hits["Value 2 years later"] = hits.value_eur_plus2.map(ui.eur)
st.dataframe(hits[["player", "season", "team", "age", "Value then", "Value 2 years later"]].rename(
    columns={"player": "Player", "season": "Flagged in", "team": "Team", "age": "Age"}),
    hide_index=True, width="stretch")

with st.expander("Method and limitations"):
    st.markdown(f"""
- **No look-ahead.** Each season's picks come from a model trained only on that season and earlier, with
  predictions made out-of-fold by player.
- **Fair comparison.** Growth is measured against players from the same season, age band and value quintile,
  so the result is not just "young, cheap players go up". Percentages are geometric means of log changes.
- **Why the market model wins.** It prices team strength and league like the market does, so its gap isolates
  players who outperform their club's market tier. Those players tend to get re-priced, often through a transfer.
- **2019/20 is flattered** by the post-COVID market rebound. The other four seasons each beat their peers
  by +25% to +34%.
- **Survivorship.** Players with no Transfermarkt value two years later (retired or untracked) are excluded.
- **Defensive data.** Understat has no tackles, interceptions or aerials, so the model under-describes defenders.
- **Snapshot.** Transfermarkt data runs to 6 July 2026; positions and contract dates are as of that snapshot.
""")
