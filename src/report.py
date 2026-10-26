"""AI scouting reports: turn a player's numbers into a short written report with Gemini.

Uses the Gemini Interactions API with streaming, so the report appears as it is written.

Key safety: the key is read server-side from st.secrets, sent only in a request header, never logged
or shown. Spend is capped three ways: finished reports are cached for every visitor (one call per
player-season, ever), each browser session may generate a few, and the whole app has an hourly cap.
"""
import json
import logging
import threading
import time
from collections import deque
from collections.abc import Iterator

import pandas as pd
import requests

from fmt import eur

MODEL = "gemini-3.6-flash"
ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/interactions?alt=sse"
MAX_OUTPUT_TOKENS = 2000  # thinking tokens count against this budget

SYSTEM_PROMPT = """You are a senior football recruitment analyst writing for a sporting director at a club with a limited transfer budget.
Write a concise scouting report from the data provided. Rules:
- Use only the numbers given. Do not invent injuries, personality, transfer rumours or anything not in the data.
- Percentiles compare the player with others in the same position group and season across Europe's Big 5 leagues.
- The model value comes from a model trained on how the market prices output, age, playing time, team strength and league. A positive value gap means the model rates the player above his market value.
- The data has no defensive actions (tackles, interceptions, aerials). For defenders say so, and judge them only on ball progression and involvement.
- Write money exactly as given (e.g. €800k, €3m, €8.7m).
- Format in Markdown with these sections: **Verdict** (one sentence), **Strengths**, **Concerns**, **Value case**, **Recommendation** (Sign / Monitor / Pass, with a one-line reason). Keep it under 250 words."""


SESSION_LIMIT = 5        # new reports per browser session
HOURLY_LIMIT = 40        # new reports per hour across all visitors

log = logging.getLogger(__name__)


class ReportError(RuntimeError):
    """Safe to show to users: never contains upstream response bodies or the key."""


class Budget:
    """Process-wide sliding-window counter of report generations."""

    def __init__(self, per_hour: int):
        self.per_hour = per_hour
        self.calls: deque[float] = deque()
        self.lock = threading.Lock()

    def try_acquire(self) -> bool:
        with self.lock:
            now = time.time()
            while self.calls and now - self.calls[0] > 3600:
                self.calls.popleft()
            if len(self.calls) >= self.per_hour:
                return False
            self.calls.append(now)
            return True


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
        "market_value": eur(player.value_eur), "model_value": eur(player.pred_value_eur),
        "value_gap_ratio": round(float(player.pred_value_eur / player.value_eur), 2),
        "statistically_similar_players": [
            {"name": r.tm_name, "team": r.team, "age": round(r.age, 1), "market_value": eur(r.value_eur)}
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
    try:
        yield from _stream(api_key, body)
    except requests.RequestException as e:
        log.warning("Gemini request error: %s", type(e).__name__)
        raise ReportError("Couldn't reach the AI service. Please try again.") from None


def _stream(api_key: str, body: dict) -> Iterator[str]:
    with requests.post(ENDPOINT, json=body, stream=True, timeout=120,
                       headers={"content-type": "application/json", "x-goog-api-key": api_key.strip()}) as r:
        if not r.ok:
            # Details go to the server log only; users get a generic message.
            log.warning("Gemini request failed: HTTP %s %s", r.status_code, r.text[:300])
            raise ReportError("The AI service is unavailable right now. Please try again in a minute.")
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
