"""Extract day-level entries from .docx chat logs.

Detection rule for day headers:
- Paragraph contains text.
- At least one run in the paragraph is bold and has font size 14pt.

Outputs JSONL records to data/raw_days.jsonl.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable, List

from docx import Document

ROOT_DIR = Path(__file__).resolve().parents[1]
OUTPUT_PATH = ROOT_DIR / "data" / "raw_days.jsonl"


@dataclass
class RawDayRecord:
    source_file: str
    day_header: str
    content_lines: List[str]
    content_text: str


def list_docx_files(root_dir: Path) -> List[Path]:
    return sorted(root_dir.glob("*.docx"))


def is_day_header_paragraph(paragraph) -> bool:
    if not paragraph.text or not paragraph.text.strip():
        return False

    return any(
        run.bold is True and run.font.size is not None and abs(run.font.size.pt - 14.0) < 0.01
        for run in paragraph.runs
    )


def extract_days_from_docx(path: Path) -> Iterable[RawDayRecord]:
    document = Document(path)

    current_header: str | None = None
    current_lines: List[str] = []

    def flush_current() -> RawDayRecord | None:
        if current_header is None:
            return None
        joined_text = "\n".join(current_lines).strip()
        return RawDayRecord(
            source_file=path.name,
            day_header=current_header,
            content_lines=current_lines.copy(),
            content_text=joined_text,
        )

    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        if not text:
            continue

        if is_day_header_paragraph(paragraph):
            previous = flush_current()
            if previous is not None:
                yield previous
            current_header = text
            current_lines = []
        elif current_header is not None:
            current_lines.append(text)

    last = flush_current()
    if last is not None:
        yield last


def write_jsonl(records: Iterable[RawDayRecord], output_path: Path) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0

    with output_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")
            count += 1

    return count


def main() -> None:
    docx_files = list_docx_files(ROOT_DIR)
    if not docx_files:
        print(f"No .docx files found in {ROOT_DIR}.")
        return

    all_records: List[RawDayRecord] = []
    for docx_path in docx_files:
        all_records.extend(extract_days_from_docx(docx_path))

    total = write_jsonl(all_records, OUTPUT_PATH)
    print(f"Wrote {total} day records to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
