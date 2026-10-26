"""Join Understat player-seasons to Transfermarkt players and market values.

Output: data/processed/player_seasons.parquet, one row per Understat player-season
with Transfermarkt id, age, position, end-of-season market value and future values.
"""
import pandas as pd
from rapidfuzz import fuzz, process

from common import BIG5, PROCESSED, RAW, norm_club, norm_name, season_of

# Understat team title -> Transfermarkt club name, where fuzzy matching gets it wrong.
TEAM_OVERRIDES = {("FR1", "Rennes"): "Stade Rennais FC"}
# A name must be a near-exact match: surname-only matches ("Marco" vs "Davide Faraoni") are rejected.
MIN_NAME_SCORE = 88


def load():
    us = pd.read_parquet(RAW / "understat" / "players.parquet")
    tm_players = pd.read_csv(RAW / "transfermarkt" / "players.csv.gz", parse_dates=["date_of_birth", "contract_expiration_date"])
    clubs = pd.read_csv(RAW / "transfermarkt" / "clubs.csv.gz")
    vals = pd.read_csv(RAW / "transfermarkt" / "player_valuations.csv.gz", parse_dates=["date"])
    vals["season"] = vals["date"].map(season_of)
    # Valuations only carry each player's *latest* club id, so club history comes from appearances.
    apps = pd.read_csv(RAW / "transfermarkt" / "appearances.csv.gz",
                       usecols=["player_id", "player_club_id", "date", "competition_id"], parse_dates=["date"])
    apps = apps[apps.competition_id.isin(BIG5)]
    apps["season"] = apps["date"].map(season_of)
    stints = apps[["player_id", "season", "player_club_id", "competition_id"]].drop_duplicates()
    return us, tm_players, clubs, vals, stints


def build_team_map(us, clubs, stints):
    """(competition_id, understat team title) -> Transfermarkt club_id."""
    comp_clubs = (stints[["competition_id", "player_club_id"]].drop_duplicates()
                  .merge(clubs[["club_id", "name"]], left_on="player_club_id", right_on="club_id"))
    by_name = clubs.set_index("name")["club_id"]
    team_map = {}
    for comp, team in us.assign(team=us.team.str.split(",")).explode("team")[["competition_id", "team"]].drop_duplicates().values:
        if (comp, team) in TEAM_OVERRIDES:
            team_map[(comp, team)] = int(by_name[TEAM_OVERRIDES[(comp, team)]])
            continue
        cand = comp_clubs[comp_clubs.competition_id == comp]
        choices = {r.club_id: norm_club(r.name) for r in cand.itertuples()}
        _, _, club_id = process.extractOne(norm_club(team), choices, scorer=fuzz.WRatio)
        team_map[(comp, team)] = int(club_id)
    return team_map


def match_players(us, tm_players, stints, team_map):
    """Map each understat_id to a Transfermarkt player_id via shared club-seasons + name similarity."""
    tm_cs = stints[["player_id", "season", "player_club_id"]].drop_duplicates()
    tm_names = tm_players.set_index("player_id")["name"].map(norm_name).to_dict()
    tm_full = (tm_players.first_name.fillna("") + " " + tm_players.last_name.fillna("")).map(norm_name)
    tm_full = dict(zip(tm_players.player_id, tm_full))

    us_cs = us.assign(team=us.team.str.split(",")).explode("team")
    us_cs["club_id"] = [team_map[(c, t)] for c, t in zip(us_cs.competition_id, us_cs.team)]

    # Candidate pairs: played for the same club in the same season.
    cands = (us_cs[["understat_id", "season", "club_id"]]
             .merge(tm_cs, left_on=["season", "club_id"], right_on=["season", "player_club_id"])
             [["understat_id", "player_id"]].value_counts().rename("overlap").reset_index())

    us_names = us.groupby("understat_id")["player_name"].first().map(norm_name)
    cands["name_score"] = [
        max(name_score(us_names[u], tm_names.get(p, "")), name_score(us_names[u], tm_full.get(p, "")))
        for u, p in zip(cands.understat_id, cands.player_id)
    ]
    cands = cands[cands.name_score >= MIN_NAME_SCORE]
    best = cands.sort_values(["name_score", "overlap"], ascending=False).drop_duplicates("understat_id")
    # One TM player per understat id and vice versa.
    best = best.drop_duplicates("player_id")
    return best.set_index("understat_id")[["player_id", "name_score"]]


def name_score(a: str, b: str) -> float:
    """Similarity that tolerates extra names ("Vinicius Junior" vs "Vinicius Jose ... Junior")
    but not a shared surname alone."""
    if not a or not b:
        return 0.0
    ta, tb = set(a.split()), set(b.split())
    if ta <= tb or tb <= ta:
        return 100.0
    # Nicknames among teammates: "Joe Gomez" vs "Joseph Gomez" (same surname and initial).
    pa, pb = a.split(), b.split()
    if len(pa) > 1 and len(pb) > 1 and pa[-1] == pb[-1] and pa[0][0] == pb[0][0]:
        return 90.0
    return fuzz.ratio(a, b)


def value_at(vals, player_ids, dates, window_days=240):
    """Most recent valuation on/before each date (within window) for each player."""
    q = pd.DataFrame({"player_id": player_ids.values, "asof": dates.values, "_i": range(len(player_ids))})
    q = q.dropna(subset=["player_id"]).astype({"player_id": "int64"}).sort_values("asof")
    v = vals[["player_id", "date", "market_value_in_eur"]].sort_values("date")
    m = pd.merge_asof(q, v, left_on="asof", right_on="date", by="player_id",
                      tolerance=pd.Timedelta(days=window_days), direction="backward")
    return m.set_index("_i")["market_value_in_eur"].reindex(range(len(player_ids))).values


def main():
    us, tm_players, clubs, vals, stints = load()
    team_map = build_team_map(us, clubs, stints)
    matches = match_players(us, tm_players, stints, team_map)

    df = us.join(matches, on="understat_id")
    rate = df.player_id.notna().mean()
    mins_rate = df.loc[df.minutes >= 900, "player_id"].notna().mean()
    print(f"Matched {rate:.1%} of player-seasons ({mins_rate:.1%} of those with 900+ minutes)")

    tm = tm_players[["player_id", "name", "date_of_birth", "position", "sub_position", "foot", "height_in_cm",
                     "contract_expiration_date", "country_of_citizenship", "image_url", "url",
                     "current_club_name", "market_value_in_eur"]].rename(
        columns={"name": "tm_name", "market_value_in_eur": "current_value_eur"})
    df = df.merge(tm, on="player_id", how="left")

    season_end = pd.to_datetime((df.season + 1).astype(str) + "-07-01")
    df["age"] = (season_end - df.date_of_birth).dt.days / 365.25
    df["value_eur"] = value_at(vals, df.player_id, season_end)
    for k in (1, 2):
        df[f"value_eur_plus{k}"] = value_at(vals, df.player_id, season_end + pd.DateOffset(years=k))

    PROCESSED.mkdir(parents=True, exist_ok=True)
    df.to_parquet(PROCESSED / "player_seasons.parquet", index=False)
    print(f"Saved {len(df)} rows; {df.value_eur.notna().sum()} with an end-of-season value")


if __name__ == "__main__":
    main()
