#!/usr/bin/env python3
from __future__ import annotations

import csv
import datetime as dt
import os
import re
import zipfile
from pathlib import Path
from typing import Iterable
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
OUTPUT_CSV = ROOT / "articles.csv"
TARGET_EXTENSIONS = {".md", ".txt", ".pdf", ".pptx", ".docx"}
EXCLUDED_DIRS = {".git", "node_modules", "venv", ".venv", "dist", "build"}
MAX_SUMMARY_LEN = 200


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def pick_summary(text: str, title: str) -> str:
    cleaned = normalize_text(text)
    if not cleaned:
        return ""
    summary = cleaned[:MAX_SUMMARY_LEN].strip()
    if summary == normalize_text(title):
        return ""
    return summary


def first_meaningful_line(lines: Iterable[str]) -> str:
    for line in lines:
        candidate = normalize_text(line)
        if candidate:
            return candidate
    return ""


def parse_front_matter_metadata(content: str) -> tuple[dict[str, str], str]:
    lines = content.splitlines()
    metadata: dict[str, str] = {}
    body_start = 0

    for idx, line in enumerate(lines):
        stripped = line.strip()
        if stripped == "":
            body_start = idx + 1
            break
        if ":" not in line:
            return {}, content
        key, value = line.split(":", 1)
        key = key.strip().lower()
        if key not in {"title", "summary", "tags"}:
            return {}, content
        metadata[key] = value.strip()
    else:
        body_start = len(lines)

    if metadata:
        body = "\n".join(lines[body_start:])
        return metadata, body
    return {}, content


def read_md_or_txt(path: Path) -> tuple[str, str, str]:
    content = path.read_text(encoding="utf-8", errors="ignore")
    metadata, body = parse_front_matter_metadata(content)

    if metadata:
        title = metadata.get("title") or path.stem
        summary = metadata.get("summary") or pick_summary(body, title)
        tags = metadata.get("tags", "")
        return title, summary, tags

    lines = content.splitlines()
    title = ""
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        heading_match = re.match(r"^#{1,6}\s+(.+)$", stripped)
        if heading_match:
            title = normalize_text(heading_match.group(1))
            break
        if not title:
            title = normalize_text(stripped)
            break

    if not title:
        title = path.stem

    summary_source = "\n".join(lines)
    summary = pick_summary(summary_source, title)
    return title, summary, ""


def read_docx(path: Path) -> tuple[str, str, str]:
    texts: list[str] = []
    with zipfile.ZipFile(path) as zf:
        xml_bytes = zf.read("word/document.xml")
    root = ET.fromstring(xml_bytes)
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    for para in root.findall(".//w:p", ns):
        parts = [t.text or "" for t in para.findall(".//w:t", ns)]
        para_text = normalize_text("".join(parts))
        if para_text:
            texts.append(para_text)

    title = texts[0] if texts else path.stem
    summary = pick_summary(" ".join(texts), title)
    return title, summary, ""


def read_pptx(path: Path) -> tuple[str, str, str]:
    slide_texts: list[list[str]] = []
    with zipfile.ZipFile(path) as zf:
        slide_names = sorted(
            [n for n in zf.namelist() if n.startswith("ppt/slides/slide") and n.endswith(".xml")],
            key=lambda n: int(re.search(r"slide(\d+)\.xml$", n).group(1)),
        )
        ns = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main"}
        for slide_name in slide_names:
            root = ET.fromstring(zf.read(slide_name))
            texts = [normalize_text(t.text or "") for t in root.findall(".//a:t", ns)]
            texts = [t for t in texts if t]
            slide_texts.append(texts)

    first_slide = slide_texts[0] if slide_texts else []
    if first_slide:
        title = first_slide[0]
    else:
        flattened = [t for slide in slide_texts for t in slide]
        title = flattened[0] if flattened else path.stem

    all_text = " ".join([t for slide in slide_texts for t in slide])
    summary = pick_summary(all_text, title)
    return title, summary, ""


def read_pdf(path: Path) -> tuple[str, str, str]:
    try:
        from PyPDF2 import PdfReader
    except Exception:
        return path.stem, "", ""

    reader = PdfReader(str(path))
    chunks: list[str] = []
    for page in reader.pages:
        chunks.append(page.extract_text() or "")
    text = "\n".join(chunks)

    title = first_meaningful_line(text.splitlines()) or path.stem
    summary = pick_summary(text, title)
    return title, summary, ""


def file_record(path: Path) -> dict[str, str]:
    rel_path = path.relative_to(ROOT).as_posix()
    last_modified = dt.datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds")

    try:
        ext = path.suffix.lower()
        if ext in {".md", ".txt"}:
            title, summary, tags = read_md_or_txt(path)
        elif ext == ".docx":
            title, summary, tags = read_docx(path)
        elif ext == ".pptx":
            title, summary, tags = read_pptx(path)
        elif ext == ".pdf":
            title, summary, tags = read_pdf(path)
        else:
            title, summary, tags = path.stem, "", ""
    except Exception:
        title, summary, tags = path.stem, "", ""

    return {
        "title": title,
        "summary": summary,
        "tags": tags,
        "filename": rel_path,
        "lastModified": last_modified,
    }


def should_skip_dir(dirname: str) -> bool:
    return dirname in EXCLUDED_DIRS or dirname.startswith('.')


def find_target_files() -> list[Path]:
    targets: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if not should_skip_dir(d)]
        base = Path(dirpath)
        for name in filenames:
            path = base / name
            if path.suffix.lower() in TARGET_EXTENSIONS:
                targets.append(path)
    return sorted(targets, key=lambda p: p.relative_to(ROOT).as_posix())


def generate_csv() -> None:
    records = [file_record(path) for path in find_target_files()]
    with OUTPUT_CSV.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["title", "summary", "tags", "filename", "lastModified"],
            quoting=csv.QUOTE_MINIMAL,
        )
        writer.writeheader()
        writer.writerows(records)
    print(f"Generated {OUTPUT_CSV} with {len(records)} records")


if __name__ == "__main__":
    generate_csv()
