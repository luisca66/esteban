# Longitudinal Evaluation Project

Base structure for extracting day-level data from `.docx` files, building a normalized dataset, and generating lightweight evaluation outputs.

## Project Structure

- `src/extract_days.py`: reads root `.docx` files and extracts day blocks into `data/raw_days.jsonl`.
- `src/build_dataset.py`: normalizes extracted day text into structured fields in `data/dataset.jsonl`.
- `src/evaluate_process.py`: computes summary metrics and trend analysis into:
  - `evaluation_report.md`
  - `out/dashboard.html` (static executive dashboard)

## Requirements

- Python 3.10+
- `python-docx`

Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage

Run the pipeline from repository root:

```bash
python src/extract_days.py
python src/build_dataset.py
python src/evaluate_process.py
```

## Output Artifacts

- `data/raw_days.jsonl`
- `data/dataset.jsonl`
- `evaluation_report.md`
- `out/dashboard.html`

## Dashboard

After running `python src/evaluate_process.py`, open:

- `out/dashboard.html`

The dashboard is a single self-contained HTML file with inline CSS/JS and uses Chart.js from CDN for a monthly exercise/reading time series.

## Notes

- Header detection for days is based on paragraphs that contain at least one **bold** run with **14pt** font size.
- Normalization uses lightweight keyword heuristics (no heavy external NLP dependencies).
