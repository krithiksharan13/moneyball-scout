"""Score every player-season with the market value model and write the app's data file."""
import numpy as np
import pandas as pd

import features as F
import value_model as M
from common import ROOT

OUT = ROOT / "data" / "app" / "players.parquet"

KEEP = ["player_id", "understat_id", "tm_name", "season", "team", "competition_id", "position_group",
        "sub_position", "age", "foot", "height_in_cm", "country_of_citizenship", "contract_expiration_date",
        "image_url", "url", "current_club_name", "current_value_eur", "games", "minutes", "minutes_share",
        "goals", "assists", "npg", "npxG", "xA", "xGChain", "xGBuildup", "shots", "key_passes",
        "team_ppg", "value_eur", "pred_value_eur", "value_gap"] + F.PER90_COLS


def main():
    df = F.build()
    df = df[df.value_eur > 0].reset_index(drop=True)
    df = M.score(df, M.oof_predict(df, F.MARKET_FEATURES))
    # Percentiles within season and position group, for radar charts and plain-English summaries.
    for c in F.PER90_COLS + ["minutes_share"]:
        df[f"{c}_pct"] = df.groupby(["season", "position_group"], observed=True)[c].rank(pct=True) * 100
    df["position_group"] = df.position_group.astype(str)
    df["competition_id"] = df.competition_id.astype(str)
    cols = KEEP + [c for c in df.columns if c.endswith("_pct")]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df[cols].to_parquet(OUT, index=False)
    print(f"Saved {len(df)} scored player-seasons -> {OUT}")


if __name__ == "__main__":
    main()
