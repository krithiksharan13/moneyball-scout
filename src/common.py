import html
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
BIG5 = ["GB1", "ES1", "L1", "IT1", "FR1"]

# Words that appear in club names but carry no identity ("FC Barcelona" == "Barcelona").
CLUB_NOISE = {"fc", "afc", "cf", "sc", "ac", "as", "ss", "ssc", "us", "rc", "rcd", "ud", "cd", "sd",
              "ca", "club", "de", "del", "la", "1", "04", "05", "1846", "1899", "1900",
              "1901", "1907", "1909", "1913", "football", "calcio", "sv", "vfb", "vfl", "tsg",
              "bv", "borussia", "fsv", "ogc", "stade", "olympique", "losc", "hellas", "and", "hove",
              "albion", "hotspur", "wanderers",
              "balompie", "sad", "e", "v", "spa", "bc", "acf", "fk", "ag", "kgaa"}


def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def norm_name(s: str) -> str:
    s = strip_accents(html.unescape(str(s))).lower()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def norm_club(s: str) -> str:
    return " ".join(t for t in norm_name(s).split() if t not in CLUB_NOISE) or norm_name(s)


def season_of(date) -> int:
    """Season start year for a date: Aug 2024 .. Jul 2025 -> 2024."""
    return date.year if date.month >= 8 else date.year - 1
