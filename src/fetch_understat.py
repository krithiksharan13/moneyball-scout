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
OUT = Path(__file__).resolve().parents[1] / "data" / "raw" / "understat" / "players.parquet"

NUMERIC = ["games", "time", "goals", "xG", "assists", "xA", "shots", "key_passes",
           "yellow_cards", "red_cards", "npg", "npxG", "xGChain", "xGBuildup"]

HEADERS = {"User-Agent": "Mozilla/5.0", "X-Requested-With": "XMLHttpRequest"}


def fetch(league: str, season: int) -> pd.DataFrame:
    url = f"https://understat.com/getLeagueData/{league}/{season}"
    r = requests.get(url, headers=HEADERS, timeout=60)
    r.raise_for_status()
    df = pd.DataFrame(r.json()["players"])
    df["league"] = league
    df["competition_id"] = LEAGUES[league]
    df["season"] = season
    return df


def main() -> None:
    frames = []
    for league in LEAGUES:
        for season in SEASONS:
            df = fetch(league, season)
            print(f"{league} {season}/{season + 1 - 2000}: {len(df)} players")
            frames.append(df)
            time.sleep(1)
    df = pd.concat(frames, ignore_index=True)
    df[NUMERIC] = df[NUMERIC].apply(pd.to_numeric)
    df = df.rename(columns={"id": "understat_id", "time": "minutes", "team_title": "team"})
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUT, index=False)
    print(f"Saved {len(df)} rows -> {OUT}")


if __name__ == "__main__":
    main()
