"""Shared Streamlit helpers: data loading, page shell, player picker, radar chart."""
import json

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import theme
from common import ROOT
from features import POSITION_LABELS

LEAGUES = {"GB1": "Premier League", "ES1": "La Liga", "L1": "Bundesliga", "IT1": "Serie A", "FR1": "Ligue 1"}
# Scatter charts can only carry three distinguishable colours, so positions fold into three lines.
LINES = {"FW": "Attack", "W": "Attack", "AM": "Attack", "CM": "Midfield", "FB": "Defence", "CB": "Defence"}

RADAR = {"npxG_p90_pct": "Goal threat", "shots_p90_pct": "Shots", "xA_p90_pct": "Chance creation",
         "key_passes_p90_pct": "Key passes", "xGChain_p90_pct": "Involvement",
         "xGBuildup_p90_pct": "Build-up", "minutes_share_pct": "Minutes"}


@st.cache_data
def load_players() -> pd.DataFrame:
    df = pd.read_parquet(ROOT / "data" / "app" / "players.parquet")
    df["league"] = df.competition_id.map(LEAGUES)
    df["position"] = df.position_group.map(POSITION_LABELS)
    df["line"] = df.position_group.map(LINES)
    df["season_label"] = df.season.map(season_label)
    df["gap_ratio"] = df.pred_value_eur / df.value_eur
    return df


@st.cache_data
def load_backtest() -> tuple[dict, pd.DataFrame]:
    result = json.loads((ROOT / "data" / "app" / "backtest.json").read_text(encoding="utf-8"))
    rows = pd.read_parquet(ROOT / "data" / "app" / "backtest_rows.parquet")
    return result, rows


def season_label(s: int) -> str:
    return f"{s}/{(s + 1) % 100:02d}"


def shell() -> None:
    """Sidebar (brand, theme toggle, glossary) and the stylesheet. Called once per run from app.py."""
    theme.init_from_query()
    with st.sidebar:
        st.html('<div class="mb-side-brand">⚽ Moneyball Scout</div>'
                '<div class="mb-side-sub">Find undervalued footballers</div>')
        st.toggle("🌙 Dark mode", key="dark_mode")
        st.html("""<div class="mb-glossary">
<div><b>Market value</b>: Transfermarkt's estimate of what the player costs.</div>
<div><b>Model value</b>: what players with this output, age, minutes and club level usually cost.</div>
<div><b>Gap</b>: model vs market. +100% means the model rates him at double his price.</div>
<div><b>Output</b>: production percentile vs players in the same position that season.</div>
</div>""")
    theme.inject_css()


def player_picker(players: pd.DataFrame, season: int, key: str, default_name: str | None = None) -> pd.Series:
    """Searchable player select. The last chosen player is remembered across pages."""
    pool = players[players.season == season].sort_values("tm_name")
    labels = dict(zip(pool.player_id, pool.tm_name + " · " + pool.team + " · " + pool.position))
    wanted = st.session_state.get("player_id")
    if wanted not in labels:
        named = pool[pool.tm_name == default_name].player_id
        wanted = int(named.iloc[0]) if len(named) else next(iter(labels))
    st.session_state[key] = wanted
    choice = st.selectbox("Player (type to search)", list(labels), format_func=labels.get, key=key,
                          on_change=lambda: st.session_state.update(player_id=st.session_state[key]))
    return pool[pool.player_id == choice].iloc[0]


def radar(rows: list[pd.Series], names: list[str]) -> go.Figure:
    fig = go.Figure()
    theta = list(RADAR.values())
    for row, name, color in zip(rows, names, [theme.t("s1"), theme.t("s2")]):
        r = [row[c] for c in RADAR]
        fig.add_trace(go.Scatterpolar(r=r + r[:1], theta=theta + theta[:1], name=name, fill="toself",
                                      line=dict(color=color, width=2), opacity=0.6, marker=dict(size=8),
                                      hovertemplate="%{theta}: %{r:.0f}th percentile<extra>" + name + "</extra>"))
    theme.style_fig(fig, height=400)
    fig.update_layout(
        showlegend=len(rows) > 1, margin=dict(l=80, r=80, t=30, b=40),
        polar=dict(bgcolor="rgba(0,0,0,0)",
                   radialaxis=dict(range=[0, 100], tickvals=[25, 50, 75], showticklabels=False,
                                   gridcolor=theme.t("grid"), linecolor=theme.t("axis")),
                   angularaxis=dict(gridcolor=theme.t("grid"), linecolor=theme.t("axis"),
                                    tickfont=dict(color=theme.t("ink-2"), size=12))))
    return fig
