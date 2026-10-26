"""Model-ready player-season table: per-90 output, playing time, team strength, track record."""
import numpy as np
import pandas as pd

from common import PROCESSED, RAW

MIN_MINUTES = 900

POSITION_GROUPS = {
    "Centre-Forward": "FW", "Second Striker": "FW",
    "Left Winger": "W", "Right Winger": "W",
    "Attacking Midfield": "AM",
    "Central Midfield": "CM", "Defensive Midfield": "CM", "Left Midfield": "CM", "Right Midfield": "CM",
    "Left-Back": "FB", "Right-Back": "FB",
    "Centre-Back": "CB",
}
POSITION_LABELS = {"FW": "Forward", "W": "Winger", "AM": "Attacking mid", "CM": "Central mid",
                   "FB": "Full-back", "CB": "Centre-back"}

PER90 = ["npxG", "xA", "xGChain", "xGBuildup", "shots", "key_passes", "npg", "assists"]
PER90_COLS = [f"{c}_p90" for c in PER90]

PERFORMANCE_FEATURES = PER90_COLS + [
    "minutes", "minutes_share", "age", "season", "position_group",
    "prev_output_p90", "prev_minutes", "big5_seasons",
]
MARKET_FEATURES = PERFORMANCE_FEATURES + ["competition_id", "team_xg_pm", "team_xga_pm", "team_ppg"]
CATEGORICAL = ["position_group", "competition_id"]


def team_strength() -> pd.DataFrame:
    t = pd.read_parquet(RAW / "understat" / "teams.parquet")
    return t.assign(team_xg_pm=t.team_xg / t.matches, team_xga_pm=t.team_xga / t.matches,
                    team_ppg=t.team_pts / t.matches)[
        ["competition_id", "season", "team", "matches", "team_xg_pm", "team_xga_pm", "team_ppg"]]


def build() -> pd.DataFrame:
    df = pd.read_parquet(PROCESSED / "player_seasons.parquet")
    df = df[df.player_id.notna()].copy()
    df["position_group"] = df.sub_position.map(POSITION_GROUPS)
    df = df[df.position_group.notna()]  # drops goalkeepers and unknown positions

    # A mid-season move between leagues gives two rows; keep the bigger one.
    df = df.sort_values("minutes", ascending=False).drop_duplicates(["player_id", "season"])

    # Team strength: average over the clubs listed for the player that season.
    teams = team_strength()
    ex = df[["player_id", "season", "competition_id", "team"]].assign(team=df.team.str.split(",")).explode("team")
    ex = ex.merge(teams, on=["competition_id", "season", "team"], how="left")
    agg = ex.groupby(["player_id", "season"])[["matches", "team_xg_pm", "team_xga_pm", "team_ppg"]].mean()
    df = df.join(agg, on=["player_id", "season"])

    for c in PER90:
        df[f"{c}_p90"] = df[c] / df.minutes * 90
    df["minutes_share"] = (df.minutes / (df.matches * 90)).clip(upper=1)

    # Track record: previous Big 5 season (any minutes) and number of Big 5 seasons so far.
    df = df.sort_values(["player_id", "season"])
    g = df.groupby("player_id")
    prev_output = (df.npxG + df.xA) / df.minutes.clip(lower=1) * 90
    df["prev_output_p90"] = np.where(g.season.diff() == 1, prev_output.groupby(df.player_id).shift(), np.nan)
    df["prev_minutes"] = np.where(g.season.diff() == 1, g.minutes.shift(), 0)
    df["big5_seasons"] = g.cumcount()

    df = df[(df.minutes >= MIN_MINUTES) & df.age.notna()]
    for c in CATEGORICAL:
        df[c] = df[c].astype("category")
    return df.reset_index(drop=True)
