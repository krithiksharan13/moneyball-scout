"""AI scouting reports: turn a player's numbers into a short written report with Gemini.

Uses the Gemini Interactions API with streaming, so the report appears as it is written.
"""
import json
from collections.abc import Iterator

import pandas as pd
import requests

MODEL = "gemini-3.6-flash"
ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/interactions?alt=sse"
MAX_OUTPUT_TOKENS = 2000  # thinking tokens count against this budget

SYSTEM_PROMPT = """You are a senior football recruitment analyst writing for a sporting director at a club with a limited transfer budget.
Write a concise scouting report from the data provided. Rules:
- Use only the numbers given. Do not invent injuries, personality, transfer rumours or anything not in the data.
- Percentiles compare the player with others in the same position group and season across Europe's Big 5 leagues.
- The model value comes from a model trained on how the market prices output, age, playing time, team strength and league. A positive value gap means the model rates the player above his market value.
- The data has no defensive actions (tackles, interceptions, aerials). For defenders say so, and judge them only on ball progression and involvement.
- Format in Markdown with these sections: **Verdict** (one sentence), **Strengths**, **Concerns**, **Value case**, **Recommendation** (Sign / Monitor / Pass, with a one-line reason). Keep it under 250 words."""


class ReportError(RuntimeError):
    pass


def build_prompt(player: pd.Series, similar: pd.DataFrame) -> str:
    pct_cols = {"npxG_p90_pct": "non-penalty xG", "xA_p90_pct": "expected assists", "xGChain_p90_pct": "xGChain",
                "xGBuildup_p90_pct": "xGBuildup", "shots_p90_pct": "shots", "key_passes_p90_pct": "key passes",
                "minutes_share_pct": "share of team minutes"}
    contract = player.contract_expiration_date
    facts = {
        "name": player.tm_name, "season": f"{player.season}/{(player.season + 1) % 100:02d}", "team": player.team,
        "position": player.sub_position, "age_at_season_end": round(player.age, 1), "foot": player.foot,
        "nationality": player.country_of_citizenship,
        "contract_until": None if pd.isna(contract) else str(pd.Timestamp(contract).date()),
        "minutes": int(player.minutes), "games": int(player.games),
        "goals": int(player.goals), "assists": int(player.assists),
        "per_90": {c.replace("_p90", ""): round(player[c], 2) for c in
                   ["npxG_p90", "xA_p90", "xGChain_p90", "xGBuildup_p90", "shots_p90", "key_passes_p90"]},
        "percentiles_vs_position": {label: round(player[c]) for c, label in pct_cols.items()},
        "market_value_eur": int(player.value_eur), "model_value_eur": int(player.pred_value_eur),
        "value_gap_ratio": round(float(player.pred_value_eur / player.value_eur), 2),
        "statistically_similar_players": [
            {"name": r.tm_name, "team": r.team, "age": round(r.age, 1), "market_value_eur": int(r.value_eur)}
            for r in similar.itertuples()
        ],
    }
    return "Write the scouting report for this player.\n\n" + json.dumps(facts, indent=1, default=str)


def stream_report(api_key: str, prompt: str) -> Iterator[str]:
    body = {
        "model": MODEL,
        "system_instruction": SYSTEM_PROMPT,
        "input": prompt,
        "stream": True,
        "generation_config": {"max_output_tokens": MAX_OUTPUT_TOKENS, "thinking_level": "minimal"},
    }
    with requests.post(ENDPOINT, json=body, stream=True, timeout=120,
                       headers={"content-type": "application/json", "x-goog-api-key": api_key.strip()}) as r:
        if not r.ok:
            raise ReportError(f"Gemini returned {r.status_code}: {r.text[:300]}")
        r.encoding = "utf-8"
        # SSE events: "data: {"delta": {"type": "text", "text": "..."}}"
        for line in r.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if not data or data == "[DONE]":
                continue
            try:
                delta = json.loads(data).get("delta") or {}
            except json.JSONDecodeError:
                continue
            if delta.get("type") == "text" and delta.get("text"):
                yield delta["text"]
