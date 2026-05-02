"""Load markdown support articles into deterministic retrievable chunks."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable, List

from schemas import DocumentChunk


COMPANY_DIRS = {
    "HackerRank": "hackerrank",
    "Claude": "claude",
    "Visa": "visa",
}


def normalize_label(value: str) -> str:
    value = value.strip().lower().replace("&", "and")
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return re.sub(r"_+", "_", value).strip("_")


class CorpusLoader:
    """Loads local markdown corpus files from data/."""

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = Path(data_dir)

    def load(self) -> List[DocumentChunk]:
        chunks: List[DocumentChunk] = []
        for company, dirname in COMPANY_DIRS.items():
            root = self.data_dir / dirname
            if not root.exists():
                continue
            for path in sorted(root.rglob("*.md")):
                text = path.read_text(encoding="utf-8", errors="replace")
                rel_path = path.relative_to(self.data_dir).as_posix()
                title = self._extract_title(text, path)
                category = self._category_for(company, path.relative_to(root))
                for chunk_text in self._split_markdown(text):
                    if self._is_substantive_chunk(chunk_text, title):
                        chunks.append(
                            DocumentChunk(
                                company=company,
                                path=rel_path,
                                category=category,
                                title=title,
                                text=chunk_text,
                            )
                        )
        return chunks

    def _extract_title(self, text: str, path: Path) -> str:
        for line in self._strip_frontmatter(text).splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                return self._clean_inline(stripped.lstrip("#").strip()) or self._title_from_filename(path)
        return self._title_from_filename(path)

    def _title_from_filename(self, path: Path) -> str:
        stem = re.sub(r"^\d+[-_]*", "", path.stem)
        return re.sub(r"[-_]+", " ", stem).strip().title()

    def _category_for(self, company: str, relative_path: Path) -> str:
        parts = list(relative_path.parts)
        if not parts:
            return "general_support"

        normalized = [normalize_label(part.removesuffix(".md")) for part in parts]

        if company == "HackerRank":
            top = normalized[0]
            if top == "hackerrank_community":
                return "community"
            if top in {"screen", "settings", "interviews", "integrations", "library"}:
                return top
            return top or "general_support"

        if company == "Claude":
            top = normalized[0]
            if top == "privacy_and_legal":
                return "privacy"
            if top == "claude" and len(normalized) > 1:
                return normalized[1]
            if top == "team_and_enterprise_plans" and len(normalized) > 1:
                return normalized[1]
            return top or "general_support"

        if company == "Visa":
            joined = "/".join(normalized)
            if "travel_support" in joined or "travelers_cheques" in joined:
                return "travel_support"
            if "dispute_resolution" in joined:
                return "dispute_resolution"
            if "fraud_protection" in joined:
                return "fraud_protection"
            if "data_security" in joined:
                return "data_security"
            if "regulations_fees" in joined or "visa_rules" in joined:
                return "rules_and_fees"
            return "general_support"

        return "general_support"

    def _split_markdown(self, text: str, max_chars: int = 2800) -> Iterable[str]:
        text = self._strip_frontmatter(text)
        sections: List[str] = []
        current: List[str] = []
        for line in text.splitlines():
            if line.startswith("#") and current:
                sections.append("\n".join(current).strip())
                current = [line]
            else:
                current.append(line)
        if current:
            sections.append("\n".join(current).strip())

        for section in sections:
            if len(section) <= max_chars:
                yield self._clean_text(section)
                continue
            paragraphs = re.split(r"\n\s*\n", section)
            buf: List[str] = []
            size = 0
            for paragraph in paragraphs:
                paragraph = paragraph.strip()
                if not paragraph:
                    continue
                if buf and size + len(paragraph) > max_chars:
                    yield self._clean_text("\n\n".join(buf))
                    buf = [paragraph]
                    size = len(paragraph)
                else:
                    buf.append(paragraph)
                    size += len(paragraph)
            if buf:
                yield self._clean_text("\n\n".join(buf))

    def _clean_text(self, text: str) -> str:
        cleaned_lines: List[str] = []
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                cleaned_lines.append("")
                continue
            if self._is_noise_line(stripped):
                continue
            stripped = self._clean_inline(stripped)
            if stripped:
                cleaned_lines.append(stripped)

        text = "\n".join(cleaned_lines)
        text = re.sub(r"\n{3,}", "\n\n", text.strip())
        return text

    def _strip_frontmatter(self, text: str) -> str:
        lines = text.splitlines()
        if lines and lines[0].strip() == "---":
            for index, line in enumerate(lines[1:], start=1):
                if line.strip() == "---":
                    return "\n".join(lines[index + 1 :])
        return text

    def _is_noise_line(self, line: str) -> bool:
        lower = line.lower()
        if re.match(r"^(title|description|url|image|og:|twitter:)\s*:", lower):
            return True
        if "last modified:" in lower or "last updated:" in lower:
            return True
        if set(line) <= {"-", "_", "*"}:
            return True
        if lower in {"table of contents", "related articles", "was this article helpful?"}:
            return True
        if lower.startswith("![") or lower.startswith("embedded media"):
            return True
        if "assets.usepylon.com" in lower or "downloads.intercomcdn.com" in lower or "cdn-cgi" in lower:
            return True
        return False

    def _clean_inline(self, text: str) -> str:
        text = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", text)
        text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
        text = re.sub(r"`([^`]+)`", r"\1", text)
        text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
        text = re.sub(r"_([^_]+)_", r"\1", text)
        text = re.sub(r"__([^_]+)__", r"\1", text)
        text = re.sub(r"<[^>]+>", "", text)
        text = text.replace("\\", "")
        return re.sub(r"\s+", " ", text).strip()

    def _is_substantive_chunk(self, text: str, title: str) -> bool:
        compact_text = normalize_label(text)
        compact_title = normalize_label(title)
        if not compact_text:
            return False
        if compact_text == compact_title:
            return False
        return len(re.findall(r"[A-Za-z0-9]+", text)) >= 8
