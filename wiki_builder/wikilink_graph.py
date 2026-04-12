"""
wikilink_graph.py — Auto-generates [[wikilinks]] between wiki articles.

After every build, scans all articles and inserts [[wikilinks]] wherever
one article's title appears in another article's body (plain text).

This is what makes Karpathy's Graph View work — connections between concepts.
The more topics you build, the richer the graph becomes.
"""

from __future__ import annotations

import re
from pathlib import Path
from collections import defaultdict


class WikilinkGraph:
    """
    Manages the wikilink graph across all articles in the vault.

    Usage:
        graph = WikilinkGraph(vault / "wiki")
        graph.rebuild_links()   # run after every build
        stats = graph.get_stats()
    """

    def __init__(self, wiki_dir: Path):
        self.wiki_dir = wiki_dir

    def rebuild_links(self) -> dict:
        """
        Scan all articles, inject [[wikilinks]] for cross-references.
        Returns stats: {injected: N, articles_updated: N}
        """
        articles = self._load_all_articles()
        if len(articles) < 2:
            return {"injected": 0, "articles_updated": 0}

        titles = [a["title"] for a in articles if a["title"]]
        # Sort by length descending — match longer titles first to avoid partial matches
        titles_sorted = sorted(titles, key=len, reverse=True)

        total_injected = 0
        articles_updated = 0

        for article in articles:
            new_body, count = self._inject_links_in_body(
                article["body"],
                article["title"],
                titles_sorted,
            )
            if count > 0:
                new_content = article["frontmatter"] + "\n\n" + new_body + "\n"
                article["path"].write_text(new_content, encoding="utf-8")
                total_injected += count
                articles_updated += 1

        return {"injected": total_injected, "articles_updated": articles_updated}

    def get_link_map(self) -> dict[str, list[str]]:
        """
        Returns {article_title: [linked_titles]} for all articles.
        Useful for generating the index.
        """
        articles = self._load_all_articles()
        link_map: dict[str, list[str]] = {}

        for article in articles:
            wikilinks = re.findall(r"\[\[([^\]]+)\]\]", article["body"])
            link_map[article["title"]] = list(set(wikilinks))

        return link_map

    def get_backlink_map(self) -> dict[str, list[str]]:
        """Returns {article_title: [titles_that_link_to_it]}"""
        forward = self.get_link_map()
        backward: dict[str, list[str]] = defaultdict(list)

        for source_title, linked_titles in forward.items():
            for linked_title in linked_titles:
                backward[linked_title].append(source_title)

        return dict(backward)

    def get_stats(self) -> dict:
        """Summary statistics for the wikilink graph."""
        articles = self._load_all_articles()
        link_map = self.get_link_map()

        total_links = sum(len(v) for v in link_map.values())
        orphans = [t for t, links in link_map.items() if not links]
        backlinks = self.get_backlink_map()
        isolated = [t for t in link_map if t not in backlinks]

        return {
            "total_articles": len(articles),
            "total_links": total_links,
            "avg_links_per_article": round(total_links / max(len(articles), 1), 1),
            "orphan_articles": len(orphans),
            "isolated_articles": len(isolated),
            "most_linked": self._most_linked(backlinks),
        }

    def _most_linked(self, backlinks: dict) -> list[tuple[str, int]]:
        """Return top 5 most-linked articles."""
        counts = [(title, len(links)) for title, links in backlinks.items()]
        return sorted(counts, key=lambda x: x[1], reverse=True)[:5]

    def _load_all_articles(self) -> list[dict]:
        """Load all wiki articles, splitting frontmatter from body."""
        articles = []
        for md_file in sorted(self.wiki_dir.glob("*.md")):
            if md_file.name.startswith("_"):
                continue
            content = md_file.read_text(encoding="utf-8")
            parsed = self._split_frontmatter(content, md_file)
            if parsed:
                articles.append(parsed)
        return articles

    def _split_frontmatter(self, content: str, path: Path) -> dict | None:
        """Split YAML frontmatter from body."""
        if not content.startswith("---"):
            return {"title": path.stem, "frontmatter": "", "body": content, "path": path}

        end = content.find("---", 3)
        if end == -1:
            return None

        frontmatter = content[:end + 3]
        body = content[end + 3:].strip()

        # Extract title from frontmatter
        title_match = re.search(r'^title:\s*["\']?([^"\'\n]+)["\']?', frontmatter, re.MULTILINE)
        title = title_match.group(1).strip() if title_match else path.stem

        return {"title": title, "frontmatter": frontmatter, "body": body, "path": path}

    def _inject_links_in_body(
        self,
        body: str,
        current_title: str,
        all_titles: list[str],
    ) -> tuple[str, int]:
        """
        Inject [[wikilinks]] into body for titles that appear as plain text.
        - Skip: current article's own title
        - Skip: already-linked occurrences
        - Link: only first occurrence of each title
        Returns (new_body, count_injected)
        """
        injected = 0
        modified = body

        for title in all_titles:
            # Don't link to self
            if title.lower() == current_title.lower():
                continue
            # Skip short titles to avoid false matches
            if len(title) < 4:
                continue

            # Pattern: title appears as plain text (not already inside [[ ]])
            pattern = re.compile(
                r'(?<!\[\[)(?<!\[)\b' + re.escape(title) + r'\b(?!\]\])(?!\])',
                re.IGNORECASE
            )

            if pattern.search(modified):
                # Replace only first occurrence
                modified = pattern.sub(f"[[{title}]]", modified, count=1)
                injected += 1

        return modified, injected
