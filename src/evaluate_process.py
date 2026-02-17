"""Evaluate normalized longitudinal dataset and generate report artifacts."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Iterable

ROOT_DIR = Path(__file__).resolve().parents[1]
DATASET_INPUT = ROOT_DIR / "data" / "dataset.jsonl"
REPORT_OUTPUT = ROOT_DIR / "evaluation_report.md"
DASHBOARD_OUTPUT = ROOT_DIR / "out" / "dashboard.html"


@dataclass
class Metrics:
    total_days: int
    exercise_rate: float
    reading_rate: float
    smoking_mentions_rate: float
    medication_mentions_rate: float
    consistency_streak: int
    trend_summary: str


def load_jsonl(path: Path) -> Iterable[dict]:
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


def safe_rate(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def parse_iso_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def compute_trend(rows: list[dict]) -> str:
    dated_rows = []
    for row in rows:
        parsed = parse_iso_date(row.get("date"))
        if parsed is not None:
            dated_rows.append((parsed, row))

    if len(dated_rows) < 4:
        return "Not enough dated records to compute trend."

    dated_rows.sort(key=lambda x: x[0])
    midpoint = len(dated_rows) // 2
    early = [r for _, r in dated_rows[:midpoint]]
    late = [r for _, r in dated_rows[midpoint:]]

    def segment_stats(segment: list[dict]) -> tuple[float, float]:
        exercise = safe_rate(sum(1 for r in segment if r.get("exercise_done")), len(segment))
        reading = safe_rate(sum(1 for r in segment if r.get("reading_done")), len(segment))
        return exercise, reading

    early_ex, early_read = segment_stats(early)
    late_ex, late_read = segment_stats(late)

    exercise_delta = late_ex - early_ex
    reading_delta = late_read - early_read

    return (
        f"Exercise trend: {'up' if exercise_delta > 0 else 'down' if exercise_delta < 0 else 'flat'} "
        f"({exercise_delta:+.1%}); "
        f"Reading trend: {'up' if reading_delta > 0 else 'down' if reading_delta < 0 else 'flat'} "
        f"({reading_delta:+.1%})."
    )


def compute_longest_activity_streak(rows: list[dict]) -> int:
    dated_rows = []
    for row in rows:
        parsed = parse_iso_date(row.get("date"))
        if parsed is not None:
            dated_rows.append((parsed, row))

    if not dated_rows:
        return 0

    dated_rows.sort(key=lambda x: x[0])
    max_streak = 0
    current_streak = 0

    for _, row in dated_rows:
        has_activity = bool(row.get("exercise_done") or row.get("reading_done"))
        if has_activity:
            current_streak += 1
            max_streak = max(max_streak, current_streak)
        else:
            current_streak = 0

    return max_streak


def build_monthly_series(rows: list[dict]) -> list[dict]:
    month_data: dict[str, dict[str, int]] = defaultdict(lambda: {"exercise": 0, "reading": 0, "days": 0})

    for row in rows:
        parsed = parse_iso_date(row.get("date"))
        if parsed is None:
            continue

        bucket = parsed.strftime("%Y-%m")
        month_data[bucket]["days"] += 1
        if row.get("exercise_done"):
            month_data[bucket]["exercise"] += 1
        if row.get("reading_done"):
            month_data[bucket]["reading"] += 1

    series = []
    for month in sorted(month_data):
        values = month_data[month]
        series.append(
            {
                "month": month,
                "days": values["days"],
                "exercise": values["exercise"],
                "reading": values["reading"],
                "exercise_rate": safe_rate(values["exercise"], values["days"]),
                "reading_rate": safe_rate(values["reading"], values["days"]),
            }
        )

    return series


def evaluate(rows: list[dict]) -> Metrics:
    total = len(rows)
    exercise_count = sum(1 for r in rows if r.get("exercise_done"))
    reading_count = sum(1 for r in rows if r.get("reading_done"))
    smoking_count = sum(1 for r in rows if r.get("smoking_reference"))
    medication_count = sum(1 for r in rows if r.get("medication_reference"))

    return Metrics(
        total_days=total,
        exercise_rate=safe_rate(exercise_count, total),
        reading_rate=safe_rate(reading_count, total),
        smoking_mentions_rate=safe_rate(smoking_count, total),
        medication_mentions_rate=safe_rate(medication_count, total),
        consistency_streak=compute_longest_activity_streak(rows),
        trend_summary=compute_trend(rows),
    )


def render_markdown(metrics: Metrics, rows: list[dict]) -> str:
    energy_counts = Counter(r.get("energy_level", "unknown") for r in rows)

    return "\n".join(
        [
            "# Evaluation Report",
            "",
            "## Core Metrics",
            f"- total_days: **{metrics.total_days}**",
            f"- exercise_rate: **{metrics.exercise_rate:.1%}**",
            f"- reading_rate: **{metrics.reading_rate:.1%}**",
            f"- smoking_mentions_rate: **{metrics.smoking_mentions_rate:.1%}**",
            f"- medication_mentions_rate: **{metrics.medication_mentions_rate:.1%}**",
            f"- consistency_streak (exercise OR reading): **{metrics.consistency_streak} days**",
            "",
            "## Trend Over Time",
            f"- {metrics.trend_summary}",
            "",
            "## Energy Level Distribution",
            *(f"- {level}: {count}" for level, count in sorted(energy_counts.items())),
            "",
        ]
    )


def render_dashboard_html(metrics: Metrics, monthly_series: list[dict]) -> str:
    labels = [row["month"] for row in monthly_series]
    exercise_counts = [row["exercise"] for row in monthly_series]
    reading_counts = [row["reading"] for row in monthly_series]

    payload = {
        "labels": labels,
        "exercise": exercise_counts,
        "reading": reading_counts,
    }

    return f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Executive Dashboard</title>
  <script src=\"https://cdn.jsdelivr.net/npm/chart.js\"></script>
  <style>
    :root {{
      --bg: #0f172a;
      --panel: #111827;
      --text: #e5e7eb;
      --muted: #9ca3af;
      --accent: #3b82f6;
      --accent-2: #10b981;
    }}
    body {{ margin: 0; background: var(--bg); color: var(--text); font-family: Arial, sans-serif; }}
    .container {{ max-width: 1100px; margin: 24px auto; padding: 0 16px; }}
    h1 {{ margin-bottom: 8px; }}
    .subtitle {{ color: var(--muted); margin-bottom: 20px; }}
    .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; }}
    .card {{ background: var(--panel); border-radius: 12px; padding: 14px; }}
    .card .label {{ color: var(--muted); font-size: 13px; }}
    .card .value {{ font-size: 26px; font-weight: bold; margin-top: 8px; }}
    .chart-wrap {{ background: var(--panel); border-radius: 12px; margin-top: 16px; padding: 16px; }}
  </style>
</head>
<body>
  <div class=\"container\">
    <h1>Executive Dashboard</h1>
    <div class=\"subtitle\">Longitudinal activity summary</div>

    <div class=\"cards\">
      <div class=\"card\"><div class=\"label\">Total days processed</div><div class=\"value\">{metrics.total_days}</div></div>
      <div class=\"card\"><div class=\"label\">Exercise rate</div><div class=\"value\">{metrics.exercise_rate:.1%}</div></div>
      <div class=\"card\"><div class=\"label\">Reading rate</div><div class=\"value\">{metrics.reading_rate:.1%}</div></div>
      <div class=\"card\"><div class=\"label\">Smoking mention rate</div><div class=\"value\">{metrics.smoking_mentions_rate:.1%}</div></div>
      <div class=\"card\"><div class=\"label\">Medication mention rate</div><div class=\"value\">{metrics.medication_mentions_rate:.1%}</div></div>
      <div class=\"card\"><div class=\"label\">Consistency streak</div><div class=\"value\">{metrics.consistency_streak} days</div></div>
    </div>

    <div class=\"chart-wrap\">
      <h2>Monthly Exercise vs Reading (counts)</h2>
      <canvas id=\"monthlyChart\" height=\"120\"></canvas>
    </div>
  </div>

  <script>
    const data = {json.dumps(payload)};

    const ctx = document.getElementById('monthlyChart').getContext('2d');
    new Chart(ctx, {{
      type: 'line',
      data: {{
        labels: data.labels,
        datasets: [
          {{
            label: 'Exercise days',
            data: data.exercise,
            borderColor: '#3b82f6',
            backgroundColor: 'rgba(59,130,246,0.2)',
            tension: 0.25
          }},
          {{
            label: 'Reading days',
            data: data.reading,
            borderColor: '#10b981',
            backgroundColor: 'rgba(16,185,129,0.2)',
            tension: 0.25
          }}
        ]
      }},
      options: {{
        responsive: true,
        plugins: {{ legend: {{ labels: {{ color: '#e5e7eb' }} }} }},
        scales: {{
          x: {{ ticks: {{ color: '#cbd5e1' }}, grid: {{ color: 'rgba(148,163,184,0.2)' }} }},
          y: {{ beginAtZero: true, ticks: {{ color: '#cbd5e1' }}, grid: {{ color: 'rgba(148,163,184,0.2)' }} }}
        }}
      }}
    }});
  </script>
</body>
</html>
"""


def main() -> None:
    if not DATASET_INPUT.exists():
        raise FileNotFoundError(f"Missing dataset file: {DATASET_INPUT}. Run build_dataset.py first.")

    rows = list(load_jsonl(DATASET_INPUT))
    metrics = evaluate(rows)
    report = render_markdown(metrics, rows)
    REPORT_OUTPUT.write_text(report, encoding="utf-8")

    monthly_series = build_monthly_series(rows)
    DASHBOARD_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    dashboard_html = render_dashboard_html(metrics, monthly_series)
    DASHBOARD_OUTPUT.write_text(dashboard_html, encoding="utf-8")

    print(f"Wrote report to {REPORT_OUTPUT}")
    print(f"Wrote dashboard to {DASHBOARD_OUTPUT}")


if __name__ == "__main__":
    main()
