"""Scouting queries over the scored player table: similar players and the undervalued board."""
import numpy as np
import pandas as pd

from features import PER90_COLS

SIMILARITY_FEATURES = PER90_COLS[:6] + ["minutes_share"]  # npxG, xA, xGChain, xGBuildup, shots, key passes


def _zscores(season_df: pd.DataFrame) -> np.ndarray:
    x = season_df[SIMILARITY_FEATURES].to_numpy(float)
    return (x - x.mean(0)) / x.std(0)


def similar_players(players: pd.DataFrame, player_id: int, season: int, n: int = 10,
                    max_value: float | None = None, max_age: float | None = None,
                    same_position: bool = True) -> pd.DataFrame:
    """Players in `season` with the closest statistical profile (cosine similarity on per-90 z-scores)."""
    pool = players[players.season == season].reset_index(drop=True)
    z = _zscores(pool)
    target_idx = pool.index[pool.player_id == player_id]
    if len(target_idx) == 0:
        raise ValueError(f"player {player_id} has no 900+ minute season in {season}")
    t = z[target_idx[0]]
    sim = z @ t / (np.linalg.norm(z, axis=1) * np.linalg.norm(t))
    res = pool.assign(similarity=sim)
    res = res[res.player_id != player_id]
    if same_position:
        res = res[res.position_group == pool.loc[target_idx[0], "position_group"]]
    if max_value is not None:
        res = res[res.value_eur <= max_value]
    if max_age is not None:
        res = res[res.age <= max_age]
    return res.sort_values("similarity", ascending=False).head(n)


def undervalued(players: pd.DataFrame, season: int, max_value: float | None = None,
                max_age: float | None = None, positions: list[str] | None = None, n: int = 50) -> pd.DataFrame:
    res = players[players.season == season]
    if max_value is not None:
        res = res[res.value_eur <= max_value]
    if max_age is not None:
        res = res[res.age <= max_age]
    if positions:
        res = res[res.position_group.isin(positions)]
    return res.sort_values("value_gap", ascending=False).head(n)


def featured_pick(players: pd.DataFrame, season: int) -> str | None:
    """A showcase default: the most undervalued regular starter with solid attacking output."""
    pool = players[(players.season == season) & (players.minutes >= 1800) & (players.output_pct >= 60)
                   & (players.value_eur <= 30e6) & (players.age <= 26)
                   & players.position_group.isin(["FW", "W", "AM", "CM"])]
    return pool.sort_values("value_gap", ascending=False).tm_name.iloc[0] if len(pool) else None
