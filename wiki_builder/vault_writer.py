"""
vault_writer.py — Writes compiled articles to the Obsidian vault.

Handles:
  - Writing new wiki articles to vault/wiki/
  - Updating index.md
  - Never overwriting raw/ (Karpathy's rule: LLM can't touch raw/)
  - Maintaining a .ku-wiki-state.json manifest for update tracking
"""

from __future__ import annotations

import json
import re
import os
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from .ku_client import KUSource


STATE_FILE = ".ku-wiki-state.json"
WIKI_DIR = "wiki"
RAW_DIR = "raw"


class VaultWriter:
    """
    Manages writing to an Obsidian vault directory.

    Vault layout enforced:
      vault/
        wiki/         ← LLM writes here
        raw/          ← human drops files here. LLM NEVER touches this.
        index.md      ← master index, auto-updated
        _changelog.md ← append-only log of all builds
    """

    def __init__(self, vault_path: str | Path):
        self.vault = Path(vault_path).expanduser().resolve()
        self.wiki_dir = self.vault / WIKI_DIR
        self.raw_dir = self.vault / RAW_DIR
        self._ensure_structure()

    def _ensure_structure(self):
        self.wiki_dir.mkdir(parents=True, exist_ok=True)
        self.raw_dir.mkdir(parents=True, exist_ok=True)

    # ─── Article writing ──────────────────────────────────────────────────────

    def write_article(
        self,
        source: KUSource,
        compiled_markdown: str,
        overwrite: bool = False,
    ) -> Path:
        """
        Write a compiled wiki article to vault/wiki/<slug>.md

        Returns the path written to.
        Raises FileExistsError if article exists and overwrite=False.
        """
        slug = self._slugify(source.title)
        article_path = self.wiki_dir / f"{slug}.md"

        if article_path.exists() and not overwrite:
            # Update the ku_last_updated field instead of full overwrite
            self._update_last_updated(article_path)
            return article_path

        article_path.write_text(compiled_markdown, encoding="utf-8")
        self._log_change("BUILD", source.title, str(article_path.relative_to(self.vault)))
        return article_path

    def write_digest(self, topic: str, digest_markdown: str) -> Path:
        """Write a 'What Changed' digest note to wiki/_what-changed-<date>.md"""
        today = date.today().isoformat()
        digest_path = self.wiki_dir / f"_what-changed-{today}.md"
        digest_path.write_text(digest_markdown, encoding="utf-8")
        self._log_change("DIGEST", topic, str(digest_path.relative_to(self.vault)))
        return digest_path

    def _update_last_updated(self, path: Path):
        """Update only the ku_last_updated field in existing frontmatter."""
        content = path.read_text(encoding="utf-8")
        today = date.today().isoformat()
        updated = re.sub(
            r"ku_last_updated:.*",
            f"ku_last_updated: {today}",
            content,
        )
        path.write_text(updated, encoding="utf-8")

    # ─── Index management ─────────────────────────────────────────────────────

    def update_index(self):
        """
        Regenerate vault/index.md from all wiki articles.
        Groups by platform. Shows decay label next to each article.
        """
        articles = self._read_all_articles()
        if not articles:
            return

        # Group by platform
        by_platform: dict[str, list[dict]] = {}
        for a in articles:
            plat = a.get("ku_platform", "other")
            by_platform.setdefault(plat, []).append(a)

        lines = [
            "---",
            "title: Knowledge Universe Wiki — Index",
            f"last_updated: {date.today().isoformat()}",
            "---",
            "",
            "# Knowledge Universe Wiki",
            "",
            f"> Built with [ku-wiki](https://github.com/VLSiddarth/ku-obsidian-wiki) | "
            f"{len(articles)} articles | Updated {date.today().isoformat()}",
            "",
        ]

        # Freshness summary
        fresh = sum(1 for a in articles if a.get("ku_freshness") == "fresh")
        aging = sum(1 for a in articles if a.get("ku_freshness") == "aging")
        stale = sum(1 for a in articles if a.get("ku_freshness") == "stale")
        lines += [
            "## Knowledge freshness",
            "",
            f"- Fresh (< 6 months): **{fresh}** articles",
            f"- Aging (6-18 months): **{aging}** articles",
            f"- Stale (> 18 months): **{stale}** articles",
            "",
        ]

        # All articles alphabetically
        lines += [
            "## All articles",
            "",
        ]

        for a in sorted(articles, key=lambda x: x["title"].lower()):
            freshness = a.get("ku_freshness", "")
            freshness_icon = {"fresh": "🟢", "aging": "🟡", "stale": "🔴"}.get(freshness, "⚪")
            quality = a.get("ku_quality", "")
            quality_str = f" · q={quality:.1f}" if quality else ""
            lines.append(f"- {freshness_icon} [[{a['title']}]]{quality_str}")

        lines += ["", "---", "", "## By platform", ""]

        platform_order = ["arxiv", "paperswithcode", "github", "stackoverflow",
                          "youtube", "huggingface", "kaggle", "wikipedia",
                          "mit_ocw", "distill", "openlibrary", "other"]

        for plat in platform_order:
            if plat not in by_platform:
                continue
            plat_articles = by_platform[plat]
            lines += [f"### {plat.replace('_', ' ').title()} ({len(plat_articles)})", ""]
            for a in sorted(plat_articles, key=lambda x: x["title"].lower()):
                lines.append(f"- [[{a['title']}]]")
            lines.append("")

        index_path = self.vault / "index.md"
        index_path.write_text("\n".join(lines), encoding="utf-8")

    def _read_all_articles(self) -> list[dict]:
        """Read YAML frontmatter from all wiki articles."""
        articles = []
        for md_file in sorted(self.wiki_dir.glob("*.md")):
            if md_file.name.startswith("_"):
                continue
            meta = self._parse_frontmatter(md_file)
            if meta:
                articles.append(meta)
        return articles

    def _parse_frontmatter(self, path: Path) -> Optional[dict]:
        """Simple YAML frontmatter parser — no external dependency."""
        content = path.read_text(encoding="utf-8")
        if not content.startswith("---"):
            return None

        end = content.find("---", 3)
        if end == -1:
            return None

        frontmatter_text = content[3:end].strip()
        meta: dict = {"_file": path.stem}

        for line in frontmatter_text.splitlines():
            if ":" not in line:
                continue
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and value and not value.startswith("-"):
                meta[key] = value

        # Try to parse numeric fields
        for field in ("ku_quality", "ku_decay", "ku_age_days"):
            if field in meta:
                try:
                    meta[field] = float(meta[field])
                except ValueError:
                    pass

        return meta

    # ─── State management ─────────────────────────────────────────────────────

    def load_state(self) -> dict:
        state_path = self.vault / STATE_FILE
        if state_path.exists():
            try:
                return json.loads(state_path.read_text())
            except Exception:
                pass
        return {"topics": {}, "last_update": None, "article_count": 0}

    def save_state(self, state: dict):
        state_path = self.vault / STATE_FILE
        state["last_update"] = datetime.utcnow().isoformat()
        state["article_count"] = len(list(self.wiki_dir.glob("*.md")))
        state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    def record_topic(self, topic: str, source_count: int, coverage_score: float):
        """Record that a topic was built — for update tracking."""
        state = self.load_state()
        state.setdefault("topics", {})[topic] = {
            "last_built": date.today().isoformat(),
            "source_count": source_count,
            "coverage_score": coverage_score,
        }
        self.save_state(state)

    def get_tracked_topics(self) -> list[str]:
        state = self.load_state()
        return list(state.get("topics", {}).keys())

    # ─── Changelog ────────────────────────────────────────────────────────────

    def _log_change(self, action: str, title: str, path: str):
        changelog = self.vault / "_changelog.md"
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
        entry = f"- `{timestamp}` **{action}**: {title} → `{path}`\n"

        if not changelog.exists():
            changelog.write_text("# Wiki changelog\n\n" + entry, encoding="utf-8")
        else:
            existing = changelog.read_text(encoding="utf-8")
            changelog.write_text(existing + entry, encoding="utf-8")

    # ─── Utilities ────────────────────────────────────────────────────────────

    def get_existing_titles(self) -> list[str]:
        """Return all wiki article titles (from filenames + frontmatter)."""
        titles = []
        for md_file in self.wiki_dir.glob("*.md"):
            if md_file.name.startswith("_"):
                continue
            meta = self._parse_frontmatter(md_file)
            if meta and "title" in meta:
                titles.append(meta["title"])
            else:
                # Fallback: derive from filename
                titles.append(md_file.stem.replace("-", " ").title())
        return titles

    def article_exists(self, title: str) -> bool:
        slug = self._slugify(title)
        return (self.wiki_dir / f"{slug}.md").exists()

    @staticmethod
    def _slugify(title: str) -> str:
        slug = title.lower()
        slug = re.sub(r"[^\w\s-]", "", slug)
        slug = re.sub(r"[\s_]+", "-", slug.strip())
        slug = re.sub(r"-+", "-", slug)
        return slug[:80]
