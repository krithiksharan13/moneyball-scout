"""Walk-forward backtest: does a high value gap predict future market-value growth?

For each flag season s, models are trained only on seasons <= s (out-of-fold by player), players are
scored on their value at the end of s, and we look at how their value moved over the next two years.
Raw growth is compared with a control group of the same season, age band and value quintile, so the
result is not just "young cheap players go up".
"""
import json

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

import features as F
import value_model as M
from common import ROOT

FLAG_SEASONS = range(2019, 2024)  # 2023/24 is the last season with a 2-year outcome
SHORTLIST = 25                    # picks per season
BUDGET_EUR = 30_000_000           # a mid-table club's realistic ceiling
MODELS = {"market": F.MARKET_FEATURES, "performance": F.PERFORMANCE_FEATURES}
OUT = ROOT / "data" / "app" / "backtest.json"


def walk_forward(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for s in FLAG_SEASONS:
        train = df[df.season <= s].reset_index(drop=True)
        flagged = train.season == s
        part = train[flagged].copy()
        for name, feats in MODELS.items():
            part[f"gap_{name}"] = M.score(train, M.oof_predict(train, feats)).value_gap[flagged].values
        rows.append(part)
        print(f"flag season {s}: {flagged.sum()} players scored")
    out = pd.concat(rows, ignore_index=True)
    out["fwd2"] = np.log(out.value_eur_plus2 / out.value_eur)
    out = out[np.isfinite(out.fwd2)].copy()
    out["age_band"] = pd.cut(out.age, [0, 21, 24, 27, 30, 50])
    out["value_q"] = out.groupby("season").value_eur.transform(lambda v: pd.qcut(v.rank(method="first"), 5, labels=False))
    out["excess2"] = out.fwd2 - out.groupby(["season", "age_band", "value_q"], observed=True).fwd2.transform("mean")
    return out


def pct(log_change) -> float:
    return float(np.expm1(log_change) * 100)


def shortlist_stats(picks: pd.DataFrame) -> dict:
    return {
        "n": int(len(picks)),
        "median_value_change_pct": round(pct(picks.fwd2.median()), 1),
        "mean_excess_pct": round(pct(picks.excess2.mean()), 1),
        "hit_rate_pct": round(float((picks.excess2 > 0).mean() * 100), 1),
    }


def best_of(result: dict) -> str:
    return max(result["models"], key=lambda m: result["models"][m]["shortlist"]["mean_excess_pct"])


def evaluate(bt: pd.DataFrame) -> dict:
    bt["output_pct"] = F.output_percentile(bt)
    budget = bt[bt.value_eur <= BUDGET_EUR]
    result = {"flag_seasons": [f"{s}/{s - 1999:02d}" for s in FLAG_SEASONS], "players_scored": int(len(bt)),
              "shortlist_size_per_season": SHORTLIST, "budget_eur": BUDGET_EUR, "models": {}}
    for name in MODELS:
        gap = f"gap_{name}"
        bt[f"{gap}_decile"] = bt.groupby("season")[gap].transform(lambda g: pd.qcut(g.rank(method="first"), 10, labels=False) + 1)
        picks = budget.sort_values(gap, ascending=False).groupby("season").head(SHORTLIST)
        result["models"][name] = {
            "spearman_gap_vs_excess": round(float(spearmanr(bt[gap], bt.excess2).statistic), 3),
            "decile_excess_pct": {int(d): round(pct(v), 1) for d, v in bt.groupby(f"{gap}_decile").excess2.mean().items()},
            "shortlist": shortlist_stats(picks),
            "by_season": {int(s): shortlist_stats(g) for s, g in picks.groupby("season")},
        }
    # Naive scout baseline: pick the best attacking output per 90 within budget.
    naive = budget.assign(o=budget.npxG_p90 + budget.xA_p90).sort_values("o", ascending=False).groupby("season").head(SHORTLIST)
    result["naive_output_baseline"] = shortlist_stats(naive)
    # Trade-off: requiring real production on top of the value gap.
    result["output_filter_sensitivity"] = {
        int(t): shortlist_stats(budget[budget.output_pct >= t].sort_values(f"gap_{best_of(result)}", ascending=False)
                                .groupby("season").head(SHORTLIST))
        for t in (0, 25, 50, 75)
    }
    result["all_budget_players"] = shortlist_stats(budget)
    return result


def main():
    df = F.build()
    df = df[df.value_eur > 0].reset_index(drop=True)
    bt = walk_forward(df)
    result = evaluate(bt)
    best = result["best_model"] = best_of(result)
    picks = (bt[bt.value_eur <= BUDGET_EUR].sort_values(f"gap_{best}", ascending=False).groupby("season").head(SHORTLIST))
    result["example_picks"] = [
        {"player": r.tm_name, "season": f"{r.season}/{r.season - 1999:02d}", "team": r.team, "age": round(r.age, 1),
         "value_eur": r.value_eur, "value_eur_plus2": r.value_eur_plus2, "gap": round(getattr(r, f"gap_{best}"), 2)}
        for r in picks.sort_values("excess2", ascending=False).itertuples()
    ]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2, default=float), encoding="utf-8")
    bt.assign(age_band=bt.age_band.astype(str)).to_parquet(ROOT / "data" / "app" / "backtest_rows.parquet", index=False)
    print(json.dumps({k: v for k, v in result.items() if k != "example_picks"}, indent=2, default=float))


if __name__ == "__main__":
    main()
