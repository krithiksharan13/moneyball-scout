"""Human-friendly number formatting: €800k, €1.2m, €25m."""
import numpy as np
import pandas as pd


def eur(v) -> str:
    if v is None or pd.isna(v):
        return "–"
    v = float(v)
    sign = "-" if v < 0 else ""
    v = abs(v)
    if v < 1e6:
        return f"{sign}€{round(v / 1e3):.0f}k"
    if v < 10e6:
        s = f"{v / 1e6:.1f}".rstrip("0").rstrip(".")
        return f"{sign}€{s}m"
    return f"{sign}€{v / 1e6:.0f}m"


def pct_badge(ratio_minus_one: float) -> str:
    """+191%, -19%. Very large gains read better as multiples: 3.2×."""
    if ratio_minus_one >= 2:
        return f"{ratio_minus_one + 1:.1f}×"
    return f"{ratio_minus_one * 100:+.0f}%"


def ordinal(n: float) -> str:
    n = int(round(n))
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def log_ticks(lo: float, hi: float) -> tuple[list[float], list[str]]:
    """Tick positions and € labels for a log-scale money axis."""
    base = [1, 2, 5]
    vals = [b * 10 ** e for e in range(4, 10) for b in base]
    vals = [v for v in vals if lo / 1.5 <= v <= hi * 1.5]
    return vals, [eur(v) for v in vals]


def money_ticks(top: float, n: int = 4) -> tuple[list[float], list[str]]:
    """Evenly spaced, round € ticks from zero to just above `top` (linear axis)."""
    raw = top / n
    mag = 10 ** np.floor(np.log10(raw))
    step = next(m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= raw)
    vals = [i * step for i in range(int(np.ceil(top / step)) + 1)]
    return vals, [eur(v) if v else "€0" for v in vals]


def pct_change(log_change: float) -> str:
    return f"{np.expm1(log_change) * 100:+.0f}%"
