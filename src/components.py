"""HTML building blocks rendered with st.html. Every data value is escaped before it touches markup."""
from html import escape
from urllib.parse import urlencode

import pandas as pd
import streamlit as st

import theme
from fmt import eur, ordinal, pct_badge


def _img(url) -> str:
    if isinstance(url, str) and url.startswith("https://"):
        return f'<img class="avatar" src="{escape(url)}" alt="" loading="lazy">'
    return '<div class="avatar"></div>'


def report_href(player_id: int, season: int) -> str:
    """Card links open the Scouting Report page; the theme rides along because the link reloads the app."""
    return "player_report?" + urlencode({"pid": int(player_id), "season": int(season), "theme": theme.mode()})


def page_title(title: str, subtitle: str) -> None:
    st.html(f'<div class="mb-page-title"><h1>{escape(title)}</h1><p>{escape(subtitle)}</p></div>')


def section(title: str, subtitle: str = "") -> None:
    sub = f"<p>{escape(subtitle)}</p>" if subtitle else ""
    st.html(f'<div class="mb-section"><h3>{escape(title)}</h3>{sub}</div>')


def kpis(items: list[dict]) -> None:
    """items: {label, value, note?, accent?}"""
    tiles = []
    for i, k in enumerate(items):
        cls = "mb-kpi accent" if k.get("accent") else "mb-kpi"
        note = f'<div class="note">{escape(k["note"])}</div>' if k.get("note") else ""
        tiles.append(f'<div class="{cls}" style="animation-delay:{i * 60}ms"><div class="label">{escape(k["label"])}</div>'
                     f'<div class="value">{escape(str(k["value"]))}</div>{note}</div>')
    st.html(f'<div class="mb-kpis">{"".join(tiles)}</div>')


def steps(items: list[tuple[str, str]]) -> None:
    html = "".join(f'<div class="mb-step" style="animation-delay:{i * 80}ms"><div class="num">{i + 1}</div>'
                   f'<h4>{escape(h)}</h4><p>{escape(b)}</p></div>' for i, (h, b) in enumerate(items))
    st.html(f'<div class="mb-steps">{html}</div>')


def card_legend() -> None:
    st.html('<div class="mb-legend"><span><b>Market</b> = Transfermarkt value</span>'
            '<span><b>Model</b> = what the model thinks he is worth</span>'
            '<span><b>Badge</b> = model vs market</span>'
            '<span><b>Output</b> = production percentile vs same position</span>'
            '<span>Click a card for the full report</span></div>')


def player_cards(df: pd.DataFrame, extra_chip: str | None = None, start_rank: int = 1) -> None:
    """Responsive grid of player cards. extra_chip: column name rendered as a highlighted chip (e.g. similarity)."""
    cards = []
    for i, r in enumerate(df.itertuples()):
        gap = r.pred_value_eur / r.value_eur - 1
        badge_cls = "up" if gap >= 0 else "down"
        chips = [escape(str(r.position)), f"{r.age:.0f} yrs", f"{int(r.minutes):,} mins"]
        chip_html = "".join(f'<span class="mb-chip">{c}</span>' for c in chips)
        if extra_chip == "similarity":
            chip_html = f'<span class="mb-chip strong">{r.similarity * 100:.0f}% similar</span>' + chip_html
        out = float(r.output_pct) if pd.notna(r.output_pct) else 0.0
        cards.append(f"""
<a class="mb-card" href="{escape(report_href(r.player_id, r.season))}" target="_self" style="animation-delay:{min(i, 12) * 40}ms">
  <div class="top">{_img(r.image_url)}
    <div class="who"><div class="name">{escape(r.tm_name)}</div><div class="club">{escape(r.team)} · {escape(str(r.league))}</div></div>
    <div class="rank">#{start_rank + i}</div></div>
  <div class="mb-chips">{chip_html}</div>
  <div class="mb-values">
    <div class="v"><div class="lbl">Market</div><div class="num">{eur(r.value_eur)}</div></div>
    <div class="arrow">→</div>
    <div class="v model"><div class="lbl">Model</div><div class="num">{eur(r.pred_value_eur)}</div></div>
    <div class="mb-badge {badge_cls}">{pct_badge(gap)}</div>
  </div>
  <div class="mb-meter"><div class="row"><span>Output</span><b>{ordinal(out)} percentile</b></div>
    <div class="bar"><i style="width:{out:.0f}%"></i></div></div>
</a>""")
    st.html(f'<div class="mb-grid">{"".join(cards)}</div>')


def table(df: pd.DataFrame, columns: dict[str, tuple[str, callable]], numeric: set[str] = frozenset()) -> None:
    """Readable HTML table. columns: {col: (header, formatter)}."""
    head = "".join(f'<th class="{"num" if c in numeric else ""}">{escape(h)}</th>' for c, (h, _) in columns.items())
    rows = []
    for _, r in df.iterrows():
        cells = "".join(f'<td class="{"num" if c in numeric else ""}">{escape(str(f(r[c])))}</td>'
                        for c, (_, f) in columns.items())
        rows.append(f"<tr>{cells}</tr>")
    st.html(f'<div class="mb-table-wrap"><table class="mb-table"><thead><tr>{head}</tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table></div>')


def profile(p: pd.Series, season_label: str, contract: str) -> None:
    img = (f'<img src="{escape(p.image_url)}" alt="">' if isinstance(p.image_url, str) and p.image_url.startswith("https://")
           else "")
    st.html(f"""<div class="mb-profile">{img}<div>
<h2>{escape(p.tm_name)}</h2>
<div class="meta">{escape(p.team)} · {escape(str(p.league))} · {escape(str(p.sub_position))}</div>
<div class="mb-chips"><span class="mb-chip">Age {p.age:.1f}</span><span class="mb-chip">{escape(str(p.country_of_citizenship))}</span>
<span class="mb-chip">{escape(str(p.foot or "–")).title()} foot</span><span class="mb-chip">Contract to {escape(contract)}</span>
<span class="mb-chip">Season {escape(season_label)}</span></div></div></div>""")
