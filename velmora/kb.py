"""Load the help-center articles (Markdown with a small header)."""
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path


@dataclass(frozen=True)
class Article:
    id: str
    title: str
    category: str
    updated: date
    body: str


def parse_article(raw: str) -> Article:
    raw = raw.replace("\r\n", "\n").replace("\r", "\n")
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", raw, re.S)
    if not m:
        raise ValueError("article has no header")
    meta = dict(
        (k.strip(), v.strip())
        for k, v in (line.split(":", 1) for line in m.group(1).splitlines() if ":" in line)
    )
    body = re.sub(r"^#.*\n", "", m.group(2).strip(), count=1).strip()  # drop the H1 (title is in the header)
    return Article(meta["id"], meta["title"], meta["category"], date.fromisoformat(meta["updated"]), body)


def load_kb(kb_dir) -> list:
    arts = [parse_article(p.read_text(encoding="utf-8")) for p in sorted(Path(kb_dir).glob("*.md"))]
    if not arts:
        raise FileNotFoundError(f"no articles in {kb_dir}")
    return arts
