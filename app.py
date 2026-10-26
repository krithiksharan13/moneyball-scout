import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent / "src"))

import ui  # noqa: E402

st.set_page_config(page_title="Moneyball Scout", page_icon="⚽", layout="wide")

pages = [
    st.Page("app_pages/overview.py", title="Overview", icon="🏟️", default=True),
    st.Page("app_pages/board.py", title="Undervalued Board", icon="💎"),
    st.Page("app_pages/similar.py", title="Find Similar", icon="🔍"),
    st.Page("app_pages/player_report.py", title="Scouting Report", icon="📝"),
    st.Page("app_pages/results.py", title="Backtest", icon="📈"),
]
page = st.navigation(pages)
ui.shell()
page.run()
