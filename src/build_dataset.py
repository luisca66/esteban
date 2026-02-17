"""Build normalized longitudinal dataset from raw day-level JSONL."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, asdict
from datetime import date
from pathlib import Path
from typing import Iterable, Optional

ROOT_DIR = Path(__file__).resolve().parents[1]
RAW_INPUT = ROOT_DIR / "data" / "raw_days.jsonl"
DATASET_OUTPUT = ROOT_DIR / "data" / "dataset.jsonl"

MONTHS = {
    # Spanish
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "setiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
    # English
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}

EXERCISE_PATTERNS = [
    r"\bejercicio\b",
    r"\bgym\b",
    r"\bentren[a-z]*\b",
    r"\bcamin[a-z]*\b",
    r"\bcorr[ié]?[a-z]*\b",
    r"\brun\b",
    r"\bworkout\b",
]

READING_PATTERNS = [
    r"\ble[eí][a-z]*\b",
    r"\blectura\b",
    r"\blibro[s]?\b",
    r"\bread(ing)?\b",
]

MEDICATION_PATTERNS = [
    r"\bmedic[a-z]*\b",
    r"\bpastilla[s]?\b",
    r"\bremedio[s]?\b",
    r"\btratamiento\b",
    r"\bmedication\b",
]

SMOKING_PATTERNS = [
    r"\bfum[a-z]*\b",
    r"\bcigarrillo[s]?\b",
    r"\btabaco\b",
    r"\bvap[eoa][a-z]*\b",
    r"\bsmok(e|ing)\b",
]

POSITIVE_ENERGY = [
    "energía", "energia", "activo", "activa", "productivo", "motiv", "bien", "great", "good"
]
NEGATIVE_ENERGY = [
    "cansado", "cansada", "fatiga", "agot", "sin energía", "sin energia", "mal", "low energy", "tired"
]

MOOD_KEYWORDS = [
    "ánimo", "animo", "mood", "feliz", "triste", "ansiedad", "ansioso", "ansiosa",
    "estrés", "estres", "calma", "motiv", "deprim", "bien", "mal",
]


@dataclass
class DatasetRecord:
    date: Optional[str]
    energy_level: str
    exercise_done: bool
    reading_done: bool
    mood_notes: str
    medication_reference: bool
    smoking_reference: bool


def load_jsonl(path: Path) -> Iterable[dict]:
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


def contains_any_pattern(text: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)


def parse_date(day_header: str) -> Optional[date]:
    clean = re.sub(r"\s+", " ", day_header.strip().lower())
    # Supports: "8 septiembre 2025" or "8 de septiembre de 2025"
    match = re.search(r"(\d{1,2})\s*(?:de\s+)?([a-záéíóúñ]+)\s*(?:de\s+)?(\d{4})", clean)
    if not match:
        return None

    day_s, month_s, year_s = match.groups()
    month = MONTHS.get(month_s)
    if not month:
        return None

    try:
        return date(int(year_s), month, int(day_s))
    except ValueError:
        return None


def infer_energy_level(text: str) -> str:
    lower = text.lower()
    pos = sum(1 for token in POSITIVE_ENERGY if token in lower)
    neg = sum(1 for token in NEGATIVE_ENERGY if token in lower)

    if pos > neg:
        return "high"
    if neg > pos:
        return "low"
    return "medium"


def extract_mood_notes(text: str) -> str:
    sentences = re.split(r"(?<=[.!?])\s+|\n+", text)
    selected = [s.strip() for s in sentences if any(k in s.lower() for k in MOOD_KEYWORDS)]
    if not selected:
        return ""
    return " ".join(selected[:3])


def normalize_day(raw: dict) -> DatasetRecord:
    content = raw.get("content_text", "")
    parsed_date = parse_date(raw.get("day_header", ""))

    return DatasetRecord(
        date=parsed_date.isoformat() if parsed_date else None,
        energy_level=infer_energy_level(content),
        exercise_done=contains_any_pattern(content, EXERCISE_PATTERNS),
        reading_done=contains_any_pattern(content, READING_PATTERNS),
        mood_notes=extract_mood_notes(content),
        medication_reference=contains_any_pattern(content, MEDICATION_PATTERNS),
        smoking_reference=contains_any_pattern(content, SMOKING_PATTERNS),
    )


def write_jsonl(records: Iterable[DatasetRecord], output_path: Path) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with output_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")
            count += 1
    return count


def main() -> None:
    if not RAW_INPUT.exists():
        raise FileNotFoundError(f"Missing input file: {RAW_INPUT}. Run extract_days.py first.")

    normalized = [normalize_day(row) for row in load_jsonl(RAW_INPUT)]
    total = write_jsonl(normalized, DATASET_OUTPUT)
    print(f"Wrote {total} dataset rows to {DATASET_OUTPUT}")


if __name__ == "__main__":
    main()
