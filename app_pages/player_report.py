import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import components as c
import report
import scout
import theme
import ui
from fmt import eur, money_ticks, ordinal


@st.cache_resource
def shared_reports() -> dict:
    """Finished reports, shared by every visitor: each player-season costs at most one API call."""
    return {}


@st.cache_resource
def hourly_budget() -> report.Budget:
    return report.Budget(report.HOURLY_LIMIT)


def api_key() -> str:
    try:
        return str(st.secrets.get("GEMINI_API_KEY", "")).strip()
    except Exception:  # no secrets file configured
        return ""


players = ui.load_players()
seasons = sorted(players.season.unique(), reverse=True)

# Card links arrive as ?pid=..&season=..; adopt them once, then clear them so the picker stays in charge.
qp = st.query_params
if "pid" in qp:
    try:
        st.session_state["player_id"] = int(qp["pid"])
        st.session_state["report_season"] = int(qp.get("season", seasons[0]))
    except ValueError:
        pass
    for k in ("pid", "season"):
        qp.pop(k, None)

c.page_title("📝 Scouting Report", "Everything on one player: profile, value history and an AI-written report.")

f1, f2 = st.columns([1, 3])
default_season = st.session_state.get("report_season", seasons[0])
season = f1.selectbox("Season", seasons, index=seasons.index(default_season) if default_season in seasons else 0,
                      format_func=ui.season_label)
st.session_state["report_season"] = int(season)
with f2:
    p = ui.player_picker(players, season, key="report_player", default_name=scout.featured_pick(players, season))

contract = "–" if pd.isna(p.contract_expiration_date) else pd.Timestamp(p.contract_expiration_date).strftime("%b %Y")
c.profile(p, ui.season_label(season), contract)

gap = p.gap_ratio - 1
c.kpis([
    {"label": "Market value", "value": eur(p.value_eur), "note": "Transfermarkt, end of season"},
    {"label": "Model value", "value": eur(p.pred_value_eur), "accent": gap >= 0,
     "note": f"{gap * 100:+.0f}% vs market · {'undervalued' if gap >= 0 else 'overvalued'}"},
    {"label": "Output", "value": f"{ordinal(p.output_pct)} pct", "note": f"vs {p.position.lower()}s in {ui.season_label(season)}"},
    {"label": "Goals + assists", "value": f"{int(p.goals)} + {int(p.assists)}",
     "note": f"{int(p.minutes):,} mins · npxG {p.npxG:.1f} · xA {p.xA:.1f}"},
])

left, right = st.columns(2)
with left:
    c.section("Profile", f"Percentiles vs {p.position.lower()}s. Further out = better.")
    st.plotly_chart(ui.radar([p], [p.tm_name]), width="stretch", theme=None)
with right:
    c.section("Market value vs model value", "How the gap has moved season by season.")
    hist = players[players.player_id == p.player_id].sort_values("season")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=hist.season_label, y=hist.value_eur, name="Market", mode="lines+markers",
                             line=dict(color=theme.t("muted"), width=2), marker=dict(size=8),
                             customdata=hist.value_eur.map(eur), hovertemplate="Market %{customdata}<extra></extra>"))
    fig.add_trace(go.Scatter(x=hist.season_label, y=hist.pred_value_eur, name="Model", mode="lines+markers",
                             line=dict(color=theme.t("s1"), width=2), marker=dict(size=8),
                             customdata=hist.pred_value_eur.map(eur), hovertemplate="Model %{customdata}<extra></extra>"))
    tv, tt = money_ticks(max(hist.value_eur.max(), hist.pred_value_eur.max()))
    theme.style_fig(fig, height=400)
    fig.update_layout(hovermode="x unified")
    fig.update_yaxes(tickvals=tv, ticktext=tt, range=[0, tv[-1] * 1.02])
    fig.update_xaxes(showgrid=False)
    st.plotly_chart(fig, width="stretch", theme=None)

c.section("🤖 AI scouting report", "Written by Gemini from the numbers on this page only. "
                                   "Treat it as a starting point, not a verdict.")
store = shared_reports()
key = (int(p.player_id), int(season))
used = st.session_state.setdefault("reports_generated", 0)

if key in store:
    with st.container(border=True):
        st.markdown(store[key])
elif not api_key():
    st.info("AI reports are not enabled on this deployment.")
elif used >= report.SESSION_LIMIT:
    st.info(f"You've generated {report.SESSION_LIMIT} new reports this session. Reports other visitors have "
            "already generated still open instantly.")
elif st.button("✨ Generate report", type="primary"):
    if not hourly_budget().try_acquire():
        st.warning("The app has hit its hourly limit for new AI reports. Please try again later.")
    else:
        similar = scout.similar_players(players, int(p.player_id), season, n=5)
        try:
            with st.container(border=True):
                text = st.write_stream(report.stream_report(api_key(), report.build_prompt(p, similar)))
            store[key] = text
            st.session_state["reports_generated"] = used + 1
        except report.ReportError as e:
            st.error(str(e))
