from docx import Document
from pathlib import Path
import re

file_path = "01 Todos los chats septiembre 2025.docx"
out_dir = Path("daily")
out_dir.mkdir(exist_ok=True)

def safe_name(s: str) -> str:
    # 8 septiembre 2025 -> 2025-09-08 (si se puede), si no, nombre limpio
    s2 = re.sub(r"\s+", " ", s.strip().lower())
    return re.sub(r"[^a-z0-9áéíóúüñ ]+", "", s2).strip().replace(" ", "_")

doc = Document(file_path)

days = {}
current_day = None

for para in doc.paragraphs:
    text = para.text.strip()

    is_header = any(
        run.bold and run.font.size and run.font.size.pt == 14
        for run in para.runs
    )

    if is_header and text:
        current_day = text
        days[current_day] = []
    elif current_day:
        if text:  # filtra líneas vacías
            days[current_day].append(text)

# escribir archivos
for day, lines in days.items():
    fname = out_dir / f"{safe_name(day)}.md"
    content = day + "\n\n" + "\n".join(lines) + "\n"
    fname.write_text(content, encoding="utf-8")

print(f"Exportados {len(days)} días a: {out_dir.resolve()}")
