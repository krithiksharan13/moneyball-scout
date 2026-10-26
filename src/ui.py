"""Shared Streamlit helpers: data loading, formatting, charts, player picker."""
import json

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from common import ROOT
from features import POSITION_LABELS

LEAGUES = {"GB1": "Premier League", "ES1": "La Liga", "L1": "Bundesliga", "IT1": "Serie A", "FR1": "Ligue 1"}
ACCENT = "#16a34a"
MUTED = "#94a3b8"

RADAR = {"npxG_p90_pct": "npxG", "shots_p90_pct": "Shots", "xA_p90_pct": "xA", "key_passes_p90_pct": "Key passes",
         "xGChain_p90_pct": "xGChain", "xGBuildup_p90_pct": "xGBuildup", "minutes_share_pct": "Minutes"}


@st.cache_data
def load_players() -> pd.DataFrame:
    df = pd.read_parquet(ROOT / "data" / "app" / "players.parquet")
    df["league"] = df.competition_id.map(LEAGUES)
    df["position"] = df.position_group.map(POSITION_LABELS)
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


def eur(v: float) -> str:
    if pd.isna(v):
        return "–"
    return f"€{v / 1e6:.1f}m" if v >= 1e6 else f"€{v / 1e3:.0f}k"


def pct_change(log_change: float) -> str:
    return f"{np.expm1(log_change) * 100:+.0f}%"


def player_picker(players: pd.DataFrame, season: int, key: str, default_name: str | None = None) -> pd.Series:
    pool = players[players.season == season].sort_values("tm_name")
    labels = (pool.tm_name + " · " + pool.team + " · " + pool.position).tolist()
    ids = pool.player_id.tolist()
    # Remember the last picked player across pages.
    remembered = st.session_state.get("player_id")
    if remembered in ids:
        index = ids.index(remembered)
    elif default_name is not None and default_name in pool.tm_name.values:
        index = pool.tm_name.tolist().index(default_name)
    else:
        index = 0
    choice = st.selectbox("Player", range(len(ids)), index=index, format_func=lambda i: labels[i], key=key)
    st.session_state["player_id"] = ids[choice]
    return pool.iloc[choice]


def radar(rows: list[pd.Series], names: list[str]) -> go.Figure:
    fig = go.Figure()
    colors = [ACCENT, "#2563eb", "#f59e0b"]
    theta = list(RADAR.values())
    for row, name, color in zip(rows, names, colors):
        r = [row[c] for c in RADAR]
        fig.add_trace(go.Scatterpolar(r=r + r[:1], theta=theta + theta[:1], name=name, fill="toself",
                                      line=dict(color=color), opacity=0.55,
                                      hovertemplate="%{theta}: %{r:.0f}th percentile<extra>" + name + "</extra>"))
    fig.update_layout(polar=dict(radialaxis=dict(range=[0, 100], tickvals=[25, 50, 75], showticklabels=False)),
                      margin=dict(l=40, r=40, t=30, b=30), height=380,
                      legend=dict(orientation="h", y=-0.12, x=0.5, xanchor="center"))
    return fig


def player_table(df: pd.DataFrame, extra: dict | None = None) -> None:
    cols = {"image_url": st.column_config.ImageColumn("", width="small"),
            "tm_name": "Player", "team": "Team", "league": "League", "position": "Position",
            "age": st.column_config.NumberColumn("Age", format="%.1f"),
            "minutes": st.column_config.NumberColumn("Mins", format="%d"),
            "output_pct": st.column_config.ProgressColumn(
                "Output", min_value=0, max_value=100, format="%.0f",
                help="Production percentile vs same position and season (npxG, xA, xGChain; defenders: xGChain, xGBuildup)"),
            "value_eur": st.column_config.NumberColumn("Market value", format="€%.0f"),
            "pred_value_eur": st.column_config.NumberColumn("Model value", format="€%.0f"),
            "gap_ratio": st.column_config.NumberColumn("Model ÷ market", format="%.2f×",
                                                       help="Model value divided by market value. Above 1 = undervalued.")}
    cols.update(extra or {})
    view = df[list(cols)].copy()
    st.dataframe(view, column_config=cols, hide_index=True, width="stretch")
