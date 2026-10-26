import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import components as c
import theme
import ui
from fmt import eur

result, rows = ui.load_backtest()
best = result["models"][result["best_model"]]
s = best["shortlist"]
budget = eur(result["budget_eur"])

c.page_title("📈 Backtest", "Does a big value gap actually predict anything? We tested it on five past seasons.")

st.html(f"""<div class="mb-hero" style="padding:22px 26px">
<p><b>The test.</b> For each season from {result['flag_seasons'][0]} to {result['flag_seasons'][-1]}, the model was trained
only on data available at the time. It picked the {result['shortlist_size_per_season']} most undervalued players under
{budget}, and we checked their Transfermarkt value two years later against players of the same season, age and price
band.</p></div>""")

c.kpis([
    {"label": "Value growth vs peers", "value": f"{s['mean_excess_pct']:+.0f}%", "accent": True,
     "note": "average over two years, vs players of the same age and price band"},
    {"label": "Hit rate", "value": f"{s['hit_rate_pct']:.0f}%", "note": "of picks grew more than their peers"},
    {"label": "Picks tested", "value": s["n"], "note": f"{result['shortlist_size_per_season']} per season × 5 seasons"},
])


def bar_text(v: float) -> str:
    return f"{v:+.0f}%"


c.section("Our picks vs the alternatives", "Value growth vs comparable players, two years after being picked.")
compare = pd.DataFrame([
    ("Moneyball Scout", result["models"]["market"]["shortlist"]["mean_excess_pct"], theme.t("s1")),
    ("Performance-only model", result["models"]["performance"]["shortlist"]["mean_excess_pct"], theme.t("muted")),
    ("Naive scout (best npxG + xA)", result["naive_output_baseline"]["mean_excess_pct"], theme.t("muted")),
    (f"Every player under {budget}", result["all_budget_players"]["mean_excess_pct"], theme.t("muted")),
], columns=["strategy", "value", "color"])
fig = go.Figure(go.Bar(x=compare.value, y=compare.strategy, orientation="h", marker=dict(color=compare.color,
                       cornerradius=4), text=compare.value.map(bar_text), textposition="outside",
                       textfont=dict(color=theme.t("ink")), hovertemplate="%{y}: %{x:+.1f}%<extra></extra>"))
theme.style_fig(fig, height=260)
fig.update_layout(bargap=0.35, margin=dict(l=10, r=50, t=10, b=10))
fig.update_yaxes(autorange="reversed", tickfont=dict(color=theme.t("ink-2"), size=13), showgrid=False)
fig.update_xaxes(ticksuffix="%", range=[min(0, compare.value.min()) - 2, compare.value.max() * 1.2])
st.plotly_chart(fig, width="stretch", theme=None)

c.section("The bigger the gap, the bigger the growth",
          "All players, split into ten equal groups by value gap (1 = most overvalued, 10 = most undervalued).")
dec = best["decile_excess_pct"]
fig = go.Figure(go.Bar(x=[f"{k}" for k in dec], y=list(dec.values()),
                       marker=dict(color=[theme.t("s1") if v > 0 else theme.t("neg") for v in dec.values()], cornerradius=4),
                       text=[bar_text(v) for v in dec.values()], textposition="outside",
                       textfont=dict(color=theme.t("ink-2")), hovertemplate="Group %{x}: %{y:+.1f}% vs peers<extra></extra>"))
theme.style_fig(fig, height=360)
fig.update_layout(bargap=0.25)
fig.update_xaxes(title="Value-gap group (1 = most overvalued → 10 = most undervalued)", showgrid=False)
fig.update_yaxes(ticksuffix="%", title="Growth vs peers")
st.plotly_chart(fig, width="stretch", theme=None)

c.section("Consistent across seasons", "Every season's shortlist beat its peers.")
by = best["by_season"]
c.kpis([{"label": f"Picked in {ui.season_label(int(k))}", "value": f"{v['mean_excess_pct']:+.0f}%",
         "note": f"hit rate {v['hit_rate_pct']:.0f}%", "accent": True} for k, v in by.items()])

c.section("Value growth vs production: the trade-off",
          "Same shortlist, but only picking players above a minimum output percentile. Demanding production "
          "costs some growth but still beats the naive scout.")
sens = result["output_filter_sensitivity"]
fig = go.Figure(go.Bar(x=["No filter" if k == "0" else f"≥ {k}th pct" for k in sens],
                       y=[v["mean_excess_pct"] for v in sens.values()],
                       marker=dict(color=theme.t("s1"), cornerradius=4),
                       text=[f"{v['mean_excess_pct']:+.0f}% · hit {v['hit_rate_pct']:.0f}%" for v in sens.values()],
                       textposition="outside", textfont=dict(color=theme.t("ink-2")),
                       hovertemplate="%{x}: %{y:+.1f}% vs peers<extra></extra>"))
fig.add_hline(y=result["naive_output_baseline"]["mean_excess_pct"], line_dash="dash", line_color=theme.t("muted"),
              annotation_text="Naive scout", annotation_position="top left",
              annotation_font=dict(color=theme.t("muted")))
theme.style_fig(fig, height=340)
fig.update_layout(bargap=0.35)
fig.update_xaxes(title="Minimum output percentile", showgrid=False)
fig.update_yaxes(ticksuffix="%", title="Growth vs peers", range=[0, max(v["mean_excess_pct"] for v in sens.values()) * 1.25])
st.plotly_chart(fig, width="stretch", theme=None)

c.section("Biggest hits", "Players the model flagged, and what they were worth two years later.")
hits = pd.DataFrame(result["example_picks"]).head(12)
hits["multiple"] = hits.value_eur_plus2 / hits.value_eur
c.table(hits, {
    "player": ("Player", str), "season": ("Flagged in", str), "team": ("Team then", str),
    "age": ("Age", lambda v: f"{v:.0f}"), "value_eur": ("Value then", eur),
    "value_eur_plus2": ("2 years later", eur), "multiple": ("Change", lambda v: f"{v:.1f}×"),
}, numeric={"age", "value_eur", "value_eur_plus2", "multiple"})

with st.expander("Method and limitations"):
    st.markdown("""
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
