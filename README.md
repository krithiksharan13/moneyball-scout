# ⚽ Moneyball Scout

**Find footballers who perform like expensive players but cost a fraction of the price.**

Moneyball Scout learns how the transfer market prices players across Europe's Big 5 leagues, then flags the
players it values far above their market price. A walk-forward backtest shows those players' market values go on
to grow faster than comparable players'.

Built for the AQX Sports Analytics Data Bowl 4.0.

## The problem

Clubs on limited budgets can't compete for proven stars. Their edge has to come from signing players before the
market prices them correctly. Scouts need a shortlist of players who are underpriced *relative to what they do on
the pitch*, and some evidence that the shortlist works.

## What it does

| Page | What you get |
|---|---|
| **Undervalued Board** | Every player ranked by the gap between model value and market value, with filters for budget, age, position, league and minimum output. Cards, chart and table views, plus CSV export. |
| **Find Similar** | Pick a player you can't afford (e.g. Bukayo Saka) and get statistically similar players within your budget, with a side-by-side radar. |
| **Scouting Report** | One player's profile, market vs model value over time, and an AI-written report (Gemini) built only from the numbers shown. |
| **Backtest** | The evidence that the signal works, season by season. |

## Results

Walk-forward backtest, 2019/20 to 2023/24. Each season the model was trained only on data available at the time,
picked the 25 most undervalued players under €30m, and we measured their Transfermarkt value two years later
against players of the same season, age band and value quintile.

| Strategy (125 picks) | Value growth vs comparable players | Hit rate |
|---|---|---|
| **Moneyball Scout (market-gap model)** | **+38%** | **68%** |
| Performance-only gap model | +20% | 60% |
| Naive scout: best npxG + xA per 90 | +6% | 56% |
| Every player under €30m | 0% | 50% |

- Across all players, growth rises from **−15%** in the most overvalued tenth to **+26%** in the most undervalued tenth.
- Every one of the five seasons' shortlists beat its peers (+25% to +86%).
- **Finding:** the market re-prices youth and playing time more than production. Requiring at least
  50th-percentile output cuts the edge to +27%, though that still beats the naive scout by a wide margin. The app
  lets scouts choose where to sit on that trade-off.
- **Finding:** about 45% of the value model's signal comes from team strength and league. The market pays for the
  club badge almost as much as for output.

Value model accuracy: R² 0.85 on log market value, out-of-fold (no player is valued by a model that saw him).

## How it works

1. **Data.** Player-season stats for 19,400 Big 5 player-seasons from [Understat](https://understat.com) (npxG,
   xA, xGChain, xGBuildup, shots, key passes, minutes) and team strength (xG, xGA, points per game). These are joined to
   [Transfermarkt](https://www.transfermarkt.co.uk) market values from
   [transfermarkt-datasets](https://github.com/dcaribou/transfermarkt-datasets) (CC0). Players are matched on
   shared club-seasons plus strict name matching, which covers 98.8% of player-seasons with 900+ minutes.
2. **Features.** Per-90 output, share of team minutes, age, position, previous-season output, Big 5 experience,
   team strength and league.
3. **Value model.** LightGBM on log market value, with out-of-fold predictions grouped by player.
   Value gap = model value ÷ market value.
4. **Similarity.** Cosine similarity on standardised per-90 profiles within a season.
5. **Backtest.** Walk-forward by season, with a control group matched on age band and value quintile.
6. **App.** Streamlit, with a light/dark theme. Scouting reports are written by `gemini-3.6-flash`.

## Limitations

- **Defenders:** Understat has no defensive actions (tackles, interceptions, aerials), so defenders are judged on
  ball progression and involvement only.
- **2019/20** results are flattered by the post-COVID market rebound. The other four seasons beat their peers by
  +25% to +34%.
- **Survivorship:** players with no Transfermarkt value two years later (retired or untracked) are excluded from the backtest.
- **Snapshot dates:** the Transfermarkt snapshot runs to 6 July 2026, and positions and contract dates are as of that snapshot.
- **What market value means:** Transfermarkt values are crowd estimates, not transfer fees.

## Run it locally

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt    # macOS/Linux: .venv/bin/pip
streamlit run app.py
```

The scored data ships in `data/app/`, so the app runs without rebuilding anything. To enable AI reports, create
`.streamlit/secrets.toml` with `GEMINI_API_KEY = "..."` (this file is gitignored).

To rebuild the data from scratch, first download the Transfermarkt CSVs (`players`, `player_valuations`, `clubs`,
`appearances`) into `data/raw/transfermarkt/`, then run:

```bash
cd src
python fetch_understat.py   # Understat player and team stats
python build_dataset.py     # join to Transfermarkt
python backtest.py          # walk-forward backtest -> data/app/backtest.json
python score.py             # app data -> data/app/players.parquet
```

## Project layout

```
app.py                 Streamlit entry point
app_pages/             the five pages
src/fetch_understat.py data collection
src/build_dataset.py   Understat <-> Transfermarkt matching
src/features.py        model features and output percentile
src/value_model.py     LightGBM value model
src/backtest.py        walk-forward backtest
src/score.py           scores every player for the app
src/scout.py           similarity search and undervalued board
src/report.py          Gemini scouting reports (cached, rate limited)
src/theme.py, src/components.py, src/ui.py   UI
```

## License

Code: MIT. Transfermarkt-derived data: CC0, via transfermarkt-datasets. Understat statistics belong to Understat
and are used here for non-commercial analysis.
