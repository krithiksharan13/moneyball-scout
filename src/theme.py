"""Light/dark design tokens, the app stylesheet, and Plotly styling that follows the active theme.

Streamlit's own theme is fixed at light in config.toml; dark mode is applied per session with CSS,
so one viewer toggling it never changes the app for anyone else.
"""
import plotly.graph_objects as go
import streamlit as st

TOKENS = {
    "light": {
        "page": "#f6f7f5", "surface": "#ffffff", "surface-2": "#f0f2ee", "ink": "#0b0b0b", "ink-2": "#52514e",
        "muted": "#898781", "border": "rgba(11,11,11,0.10)", "grid": "#e1e0d9", "axis": "#c3c2b7",
        "accent": "#15803d", "accent-strong": "#16a34a", "accent-soft": "rgba(22,163,74,0.12)",
        "up": "#006300", "down": "#d03b3b", "shadow": "0 10px 30px rgba(15,23,42,0.10)",
        "hero": "linear-gradient(135deg, #ecfdf3 0%, #e0f2fe 100%)",
        # Reference palette: categorical slots 1-3, diverging poles.
        "s1": "#2a78d6", "s2": "#eb6834", "s3": "#1baf7a", "neg": "#e34948", "neutral": "#c3c2b7",
    },
    "dark": {
        "page": "#0d0d0d", "surface": "#1a1a19", "surface-2": "#262624", "ink": "#f0efec", "ink-2": "#c3c2b7",
        "muted": "#898781", "border": "rgba(255,255,255,0.10)", "grid": "#2c2c2a", "axis": "#383835",
        "accent": "#22c55e", "accent-strong": "#16a34a", "accent-soft": "rgba(34,197,94,0.14)",
        "up": "#0ca30c", "down": "#e66767", "shadow": "0 10px 30px rgba(0,0,0,0.45)",
        "hero": "linear-gradient(135deg, #0f2a1b 0%, #0f1f33 100%)",
        "s1": "#3987e5", "s2": "#d95926", "s3": "#199e70", "neg": "#e66767", "neutral": "#383835",
    },
}


def mode() -> str:
    return "dark" if st.session_state.get("dark_mode") else "light"


def t(name: str) -> str:
    return TOKENS[mode()][name]


def init_from_query() -> None:
    """Card links reload the page, so the theme travels in the URL (?theme=dark)."""
    if "dark_mode" not in st.session_state:
        st.session_state["dark_mode"] = st.query_params.get("theme") == "dark"


def inject_css() -> None:
    tok = TOKENS[mode()]
    root = "\n".join(f"  --{k}: {v};" for k, v in tok.items())
    st.html(f"<style>\n:root {{\n{root}\n}}\n{CSS}</style>")


def style_fig(fig: go.Figure, height: int = 380) -> go.Figure:
    """Transparent background, theme ink, recessive grid. Render with st.plotly_chart(..., theme=None)."""
    fig.update_layout(
        height=height, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, system-ui, -apple-system, Segoe UI, sans-serif", color=t("ink-2"), size=13),
        margin=dict(l=10, r=10, t=30, b=10),
        hoverlabel=dict(bgcolor=t("surface"), bordercolor=t("border"), font=dict(color=t("ink"))),
        legend=dict(orientation="h", y=-0.15, x=0.5, xanchor="center", font=dict(color=t("ink-2"))),
    )
    axis = dict(gridcolor=t("grid"), linecolor=t("axis"), zerolinecolor=t("axis"), tickfont=dict(color=t("muted")),
                title_font=dict(color=t("ink-2")), automargin=True)
    fig.update_xaxes(**axis)
    fig.update_yaxes(**axis)
    return fig


CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

/* ---------- Streamlit chrome ---------- */
.stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
  background: var(--page); color: var(--ink);
  font-family: Inter, system-ui, -apple-system, "Segoe UI", sans-serif;
  transition: background-color .35s ease, color .35s ease;
}
[data-testid="stHeader"] { background: transparent; }
[data-testid="stSidebar"] { background: var(--surface); border-right: 1px solid var(--border); transition: background-color .35s ease; }
[data-testid="stSidebarNav"] a span, [data-testid="stSidebarNavLink"] span { color: var(--ink-2); }
[data-testid="stSidebarNav"] a[aria-current="page"], [data-testid="stSidebarNavLink"][aria-current="page"] { background: var(--accent-soft); }
[data-testid="stSidebarNav"] a[aria-current="page"] span { color: var(--ink); font-weight: 600; }
[data-testid="stSidebarNav"] a:hover { background: var(--surface-2); }
.stApp h1, .stApp h2, .stApp h3, .stApp h4 { color: var(--ink); font-family: Inter, system-ui, sans-serif; letter-spacing: -0.02em; }
.stApp [data-testid="stMarkdownContainer"] p, .stApp [data-testid="stMarkdownContainer"] li { color: var(--ink-2); }
.stApp [data-testid="stCaptionContainer"], .stApp [data-testid="stCaptionContainer"] p { color: var(--muted); }
[data-testid="stWidgetLabel"] p, [data-testid="stWidgetLabel"] label { color: var(--ink-2) !important; font-weight: 500; }
.stApp code { background: var(--surface-2); color: var(--ink); }
.block-container { padding-top: 2.2rem; max-width: 1240px; }

/* inputs, selects, popovers */
[data-baseweb="select"] > div, [data-baseweb="input"] > div, [data-baseweb="base-input"], [data-baseweb="input"] input {
  background: var(--surface) !important; border-color: var(--border) !important; color: var(--ink) !important;
}
[data-baseweb="select"] * { color: var(--ink); }
[data-baseweb="select"] svg { fill: var(--muted); }
[data-baseweb="popover"] ul, [data-baseweb="popover"] [role="listbox"], [data-baseweb="menu"] { background: var(--surface) !important; }
[data-baseweb="popover"] li { color: var(--ink) !important; background: var(--surface); }
[data-baseweb="popover"] li:hover, [data-baseweb="popover"] li[aria-selected="true"] { background: var(--surface-2) !important; }
/* Streamlit 1.66 select / multiselect (non-BaseWeb) */
[data-testid="stSelectbox"] [role="group"], [data-testid="stMultiSelect"] [role="group"] {
  background: var(--surface) !important; border-color: var(--border) !important;
}
[data-testid="stSelectbox"] [role="group"] *, [data-testid="stMultiSelect"] [role="group"] * { color: var(--ink); }
[data-testid="stSelectbox"] input, [data-testid="stMultiSelect"] input { background: transparent !important; color: var(--ink) !important; }
[data-testid="stSelectbox"] input::placeholder, [data-testid="stMultiSelect"] input::placeholder { color: var(--muted) !important; }
[data-testid*="Dropdown"] { background: var(--surface) !important; border: 1px solid var(--border); }
[data-testid*="Dropdown"] [role="option"] { color: var(--ink) !important; }
[data-testid*="Dropdown"] [role="option"]:hover, [data-testid*="Dropdown"] [role="option"][aria-selected="true"] { background: var(--surface-2) !important; }
[data-baseweb="tag"] { background: var(--accent-soft) !important; }
[data-baseweb="tag"] span { color: var(--ink) !important; }
[data-testid="stSliderTickBarMin"], [data-testid="stSliderTickBarMax"] { color: var(--muted); }
[data-testid="stSliderThumbValue"] { color: var(--ink); font-weight: 600; }
[data-testid="stVerticalBlockBorderWrapper"] { border-color: var(--border) !important; }
div[data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stVerticalBlock"] > .filters-anchor) {
  background: var(--surface); border-radius: 16px; box-shadow: var(--shadow);
}
.stTabs [data-baseweb="tab-list"] { gap: 6px; }
.stTabs [data-baseweb="tab"] { color: var(--ink-2); }
.stTabs [aria-selected="true"] { color: var(--ink); }
.stTabs [data-baseweb="tab-highlight"] { background: var(--accent-strong); }
.stTabs [data-baseweb="tab-border"] { background: var(--border); }
.stButton > button[kind="secondary"], .stDownloadButton > button {
  background: var(--surface); color: var(--ink); border: 1px solid var(--border); border-radius: 10px;
}
.stButton > button[kind="secondary"]:hover, .stDownloadButton > button:hover { border-color: var(--accent); color: var(--accent); }
.stButton > button[kind="primary"] { border-radius: 10px; font-weight: 600; transition: transform .15s ease, box-shadow .15s ease; }
.stButton > button[kind="primary"]:hover { transform: translateY(-1px); box-shadow: 0 6px 18px rgba(22,163,74,.35); }
[data-testid="stAlert"] { background: var(--surface-2); border: 1px solid var(--border); border-radius: 12px; }
[data-testid="stAlert"] p { color: var(--ink-2) !important; }
[data-testid="stExpander"] details { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; }
[data-testid="stExpander"] summary p { color: var(--ink) !important; }
[data-testid="stToggle"] p, [data-testid="stCheckbox"] p { color: var(--ink-2); }

/* ---------- components ---------- */
@keyframes rise { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: none; } }
@keyframes grow { from { width: 0; } }
.mb-hero { background: var(--hero); border: 1px solid var(--border); border-radius: 22px; padding: 34px 34px 30px; margin-bottom: 18px; animation: rise .5s ease both; }
.mb-hero .eyebrow { color: var(--accent); font-weight: 700; font-size: .78rem; letter-spacing: .14em; text-transform: uppercase; }
.mb-hero h1 { font-size: clamp(2rem, 4vw, 3rem); margin: 6px 0 10px; line-height: 1.05; color: var(--ink); font-weight: 800; }
.mb-hero p { color: var(--ink-2); font-size: 1.08rem; max-width: 760px; margin: 0; line-height: 1.55; }
.mb-page-title { margin: 0 0 4px; animation: rise .4s ease both; }
.mb-page-title h1 { font-size: 2.1rem; font-weight: 800; margin: 0; color: var(--ink); letter-spacing: -0.02em; }
.mb-page-title p { color: var(--ink-2); margin: 4px 0 14px; font-size: 1.02rem; }
.mb-section { margin: 26px 0 10px; }
.mb-section h3 { margin: 0; font-size: 1.3rem; font-weight: 700; color: var(--ink); }
.mb-section p { margin: 4px 0 0; color: var(--muted); font-size: .95rem; }

.mb-kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 14px; margin: 8px 0 6px; }
.mb-kpi { background: var(--surface); border: 1px solid var(--border); border-radius: 16px; padding: 18px 20px; animation: rise .5s ease both; transition: transform .2s ease, box-shadow .2s ease; }
.mb-kpi:hover { transform: translateY(-3px); box-shadow: var(--shadow); }
.mb-kpi .label { color: var(--muted); font-size: .82rem; font-weight: 600; text-transform: uppercase; letter-spacing: .06em; }
.mb-kpi .value { color: var(--ink); font-size: 2.1rem; font-weight: 800; margin: 4px 0 2px; letter-spacing: -0.03em; }
.mb-kpi .note { color: var(--ink-2); font-size: .88rem; line-height: 1.4; }
.mb-kpi.accent .value { color: var(--accent); }

.mb-steps { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 14px; }
.mb-step { background: var(--surface); border: 1px solid var(--border); border-radius: 16px; padding: 18px 20px; animation: rise .5s ease both; }
.mb-step .num { display: inline-grid; place-items: center; width: 30px; height: 30px; border-radius: 50%; background: var(--accent-soft); color: var(--accent); font-weight: 800; margin-bottom: 8px; }
.mb-step h4 { margin: 0 0 6px; color: var(--ink); font-size: 1.05rem; }
.mb-step p { margin: 0; color: var(--ink-2); font-size: .93rem; line-height: 1.5; }

.mb-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(290px, 1fr)); gap: 14px; margin: 8px 0 4px; }
.mb-card { display: block; text-decoration: none !important; color: inherit !important; background: var(--surface); border: 1px solid var(--border);
  border-radius: 18px; padding: 16px 18px; animation: rise .45s ease both; transition: transform .2s ease, box-shadow .2s ease, border-color .2s ease; position: relative; }
.mb-card:hover { transform: translateY(-4px); box-shadow: var(--shadow); border-color: var(--accent); }
.mb-card .top { display: flex; align-items: center; gap: 12px; }
.mb-card .avatar { width: 48px; height: 48px; border-radius: 50%; object-fit: cover; background: var(--surface-2); flex: none; border: 2px solid var(--border); }
.mb-card .who { min-width: 0; flex: 1; }
.mb-card .name { color: var(--ink); font-weight: 700; font-size: 1.04rem; line-height: 1.25; }
.mb-card .club { color: var(--muted); font-size: .86rem; margin-top: 2px; }
.mb-card .rank { color: var(--muted); font-weight: 700; font-size: .85rem; align-self: flex-start; }
.mb-chips { display: flex; flex-wrap: wrap; gap: 6px; margin: 12px 0 10px; }
.mb-chip { background: var(--surface-2); color: var(--ink-2); border-radius: 999px; padding: 3px 10px; font-size: .8rem; font-weight: 500; }
.mb-chip.strong { background: var(--accent-soft); color: var(--accent); font-weight: 700; }
.mb-values { display: flex; align-items: flex-end; gap: 10px; padding: 10px 0 8px; border-top: 1px solid var(--border); }
.mb-values .v .lbl { color: var(--muted); font-size: .72rem; font-weight: 600; text-transform: uppercase; letter-spacing: .06em; }
.mb-values .v .num { color: var(--ink); font-size: 1.35rem; font-weight: 800; letter-spacing: -0.02em; }
.mb-values .v.model .num { color: var(--s1); }
.mb-values .arrow { color: var(--muted); font-size: 1.1rem; padding-bottom: 4px; }
.mb-badge { margin-left: auto; font-weight: 800; font-size: .9rem; padding: 4px 10px; border-radius: 999px; }
.mb-badge.up { color: var(--up); background: var(--accent-soft); }
.mb-badge.down { color: var(--down); background: rgba(227,73,72,.12); }
.mb-meter { margin-top: 6px; }
.mb-meter .row { display: flex; justify-content: space-between; color: var(--muted); font-size: .78rem; font-weight: 600; margin-bottom: 4px; }
.mb-meter .row b { color: var(--ink-2); }
.mb-meter .bar { height: 6px; border-radius: 4px; background: var(--surface-2); overflow: hidden; }
.mb-meter .bar i { display: block; height: 100%; border-radius: 4px; background: var(--s1); animation: grow .8s ease both; }

.mb-legend { display: flex; flex-wrap: wrap; gap: 16px; color: var(--muted); font-size: .85rem; margin: 2px 0 8px; }
.mb-legend b { color: var(--ink-2); }

.mb-profile { display: flex; gap: 20px; align-items: center; background: var(--surface); border: 1px solid var(--border); border-radius: 20px; padding: 20px 22px; animation: rise .45s ease both; }
.mb-profile img { width: 92px; height: 92px; border-radius: 50%; object-fit: cover; border: 3px solid var(--accent-soft); background: var(--surface-2); }
.mb-profile h2 { margin: 0; font-size: 1.8rem; color: var(--ink); font-weight: 800; }
.mb-profile .meta { color: var(--ink-2); margin-top: 4px; }

.mb-report { background: var(--surface); border: 1px solid var(--border); border-left: 4px solid var(--accent-strong); border-radius: 16px; padding: 6px 22px 10px; }

.mb-table { width: 100%; border-collapse: separate; border-spacing: 0; font-size: .92rem; background: var(--surface); border: 1px solid var(--border); border-radius: 14px; overflow: hidden; }
.mb-table th { text-align: left; color: var(--muted); font-weight: 600; font-size: .78rem; text-transform: uppercase; letter-spacing: .05em; padding: 10px 12px; background: var(--surface-2); }
.mb-table td { color: var(--ink); padding: 9px 12px; border-top: 1px solid var(--border); white-space: nowrap; }
.mb-table td.num { text-align: right; font-variant-numeric: tabular-nums; }
.mb-table th.num { text-align: right; }
.mb-table tr:hover td { background: var(--surface-2); }
.mb-table-wrap { overflow: auto; max-height: 560px; border-radius: 14px; }
.mb-table thead th { position: sticky; top: 0; z-index: 1; }

.mb-side-brand { font-weight: 800; font-size: 1.15rem; color: var(--ink); margin: 0 0 2px; }
.mb-side-sub { color: var(--muted); font-size: .85rem; margin-bottom: 10px; }
.mb-glossary { font-size: .84rem; color: var(--ink-2); line-height: 1.5; }
.mb-glossary b { color: var(--ink); }
.mb-glossary div { margin-bottom: 8px; }

@media (max-width: 640px) {
  .mb-hero { padding: 22px 18px; }
  .mb-grid { grid-template-columns: 1fr; }
  .mb-profile { flex-direction: column; text-align: center; }
}
"""
