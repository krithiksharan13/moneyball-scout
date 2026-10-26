"""Download player-season stats for the Big 5 leagues from Understat.

Understat serves each league-season as JSON at /getLeagueData/<league>/<year>,
where <year> is the season's starting year (2024 -> 2024/25).
"""
import time
from pathlib import Path

import pandas as pd
import requests

LEAGUES = {
    "EPL": "GB1",
    "La_liga": "ES1",
    "Bundesliga": "L1",
    "Serie_A": "IT1",
    "Ligue_1": "FR1",
}
SEASONS = range(2019, 2026)  # 2019/20 .. 2025/26
OUT_DIR = Path(__file__).resolve().parents[1] / "data" / "raw" / "understat"

NUMERIC = ["games", "time", "goals", "xG", "assists", "xA", "shots", "key_passes",
           "yellow_cards", "red_cards", "npg", "npxG", "xGChain", "xGBuildup"]

HEADERS = {"User-Agent": "Mozilla/5.0", "X-Requested-With": "XMLHttpRequest"}


def fetch(league: str, season: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    url = f"https://understat.com/getLeagueData/{league}/{season}"
    r = requests.get(url, headers=HEADERS, timeout=60)
    r.raise_for_status()
    data = r.json()
    meta = {"league": league, "competition_id": LEAGUES[league], "season": season}
    players = pd.DataFrame(data["players"]).assign(**meta)
    # Team-season strength from per-match history.
    teams = pd.DataFrame([
        {"team": t["title"], "matches": len(t["history"]),
         "team_xg": sum(m["xG"] for m in t["history"]), "team_xga": sum(m["xGA"] for m in t["history"]),
         "team_pts": sum(m["pts"] for m in t["history"])}
        for t in data["teams"].values()
    ]).assign(**meta)
    return players, teams


def main() -> None:
    frames, team_frames = [], []
    for league in LEAGUES:
        for season in SEASONS:
            df, teams = fetch(league, season)
            print(f"{league} {season}/{season + 1 - 2000}: {len(df)} players")
            frames.append(df)
            team_frames.append(teams)
            time.sleep(1)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    pd.concat(team_frames, ignore_index=True).to_parquet(OUT_DIR / "teams.parquet", index=False)
    df = pd.concat(frames, ignore_index=True)
    df[NUMERIC] = df[NUMERIC].apply(pd.to_numeric)
    df = df.rename(columns={"id": "understat_id", "time": "minutes", "team_title": "team"})
    df.to_parquet(OUT_DIR / "players.parquet", index=False)
    print(f"Saved {len(df)} rows -> {OUT_DIR}")


if __name__ == "__main__":
    main()
