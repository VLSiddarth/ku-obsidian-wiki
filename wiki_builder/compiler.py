"""
compiler.py — LLM compilation engine.

The LLM is the compiler. Raw sources go in. Wiki articles come out.
Uses Claude API (claude-sonnet-4-20250514) or falls back to a template-only mode.

Karpathy's principle: "Drop files in a folder, the LLM compiles them
into a living, interlinked Wikipedia."

Our addition: every compiled article carries decay metadata from KU.
"""

from __future__ import annotations

import os
import re
import textwrap
from datetime import date
from typing import Optional

from .ku_client import KUSource, KUDecay


# ─── Compilation prompt ───────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a personal knowledge wiki compiler, operating in the style described by Andrej Karpathy.

Your job: given a knowledge source (title, summary, URL, platform), compile a concise wiki article.

STRICT RULES:
1. Write in clear, dense prose. No fluff. No filler sentences.
2. 150–350 words in the body. Not more.
3. Use [[wikilinks]] for any concept that deserves its own article.
   Example: "The [[transformer architecture]] uses [[multi-head attention]]..."
4. Sentence case all headings (## What this is, ## How it works).
5. Never copy text verbatim — always synthesize and rephrase.
6. End with one sentence that places this concept in context.
7. Do NOT include YAML frontmatter — that is handled externally.
8. Do NOT include a title header (# Title) — that is handled externally.
9. Return ONLY the markdown body. Nothing else.

SECTIONS TO INCLUDE (as relevant):
## What this is
## How it works  (or ## Key ideas)
## Why it matters
## Related concepts  (use [[wikilinks]] here)

Karpathy hates vague writing. Be specific. If something has a number, use it."""


def _build_user_prompt(source: KUSource, existing_titles: list[str]) -> str:
    existing_str = "\n".join(f"- {t}" for t in existing_titles[:50]) if existing_titles else "None yet."
    decay_str = ""
    if source.decay:
        decay_str = f"Freshness: {source.decay.label} ({source.decay.age_days} days old, decay={source.decay.decay_score:.2f})"

    authors_str = ", ".join(source.authors[:3]) if source.authors else "Unknown"
    tags_str = ", ".join(source.tags[:8]) if source.tags else "none"

    return f"""Compile a wiki article for this knowledge source.

SOURCE:
Title: {source.title}
Platform: {source.platform}
URL: {source.url}
Authors: {authors_str}
Tags: {tags_str}
{decay_str}

Summary:
{source.summary[:1200]}

EXISTING WIKI ARTICLES (use [[wikilinks]] to reference these when relevant):
{existing_str}

Write the wiki article body now. 150–350 words. Dense and specific."""


# ─── Compiler class ───────────────────────────────────────────────────────────

class WikiCompiler:
    """
    Compiles KU sources into Obsidian-ready Markdown wiki articles.

    Requires ANTHROPIC_API_KEY in environment for full LLM compilation.
    Falls back to template mode if the API key is not set.
    """

    def __init__(self, anthropic_api_key: Optional[str] = None):
        self.api_key = anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self._client = None

        if self.api_key:
            try:
                import anthropic
                self._client = anthropic.Anthropic(api_key=self.api_key)
            except ImportError:
                self._client = None

    @property
    def has_llm(self) -> bool:
        return self._client is not None

    def compile(
        self,
        source: KUSource,
        existing_titles: list[str],
    ) -> str:
        """
        Compile a single KU source into a full wiki article (YAML + body).
        Returns the complete Markdown string ready to write to disk.
        """
        frontmatter = self._build_frontmatter(source)

        if self.has_llm:
            body = self._compile_with_llm(source, existing_titles)
        else:
            body = self._compile_template(source, existing_titles)

        return f"{frontmatter}\n\n{body}\n"

    def _compile_with_llm(self, source: KUSource, existing_titles: list[str]) -> str:
        """Call Claude API to synthesize the article body."""
        try:
            message = self._client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1000,
                system=SYSTEM_PROMPT,
                messages=[
                    {"role": "user", "content": _build_user_prompt(source, existing_titles)}
                ],
            )
            body = message.content[0].text.strip()
            # Inject wikilinks for known titles that appear plainly
            body = self._inject_wikilinks(body, existing_titles)
            return body
        except Exception as e:
            return self._compile_template(source, existing_titles)

    def _compile_template(self, source: KUSource, existing_titles: list[str]) -> str:
        """
        Fallback template mode — no LLM required.
        Produces a structured stub from the KU metadata.
        """
        decay = source.decay
        freshness_note = ""
        if decay:
            freshness_note = f"\n> Source freshness: **{decay.label}** ({decay.age_days} days old, decay score {decay.decay_score:.2f})\n"

        tags_str = " ".join(f"[[{t}]]" for t in source.tags[:5]) if source.tags else ""
        authors_str = ", ".join(source.authors[:3]) if source.authors else "Unknown"

        # Find relevant existing titles to link
        links = self._find_relevant_links(source.title + " " + source.summary, existing_titles)
        links_str = "\n".join(f"- [[{t}]]" for t in links[:6]) if links else "- *(add links as wiki grows)*"

        summary_wrapped = textwrap.fill(source.summary[:600], width=80) if source.summary else "No summary available."

        body = f"""## What this is

{summary_wrapped}
{freshness_note}
## Source details

- **Platform:** {source.platform.title()}
- **Authors:** {authors_str}
- **Quality score:** {source.quality_score:.1f}/10
- **URL:** [{source.title}]({source.url})

## Related concepts

{links_str}

{tags_str}"""

        return body.strip()

    def _build_frontmatter(self, source: KUSource) -> str:
        """Build YAML frontmatter with KU metadata — the core innovation."""
        today = date.today().isoformat()
        decay = source.decay

        slug_title = self._slugify(source.title)

        # Build decay block
        if decay:
            decay_block = f"""ku_quality: {source.quality_score:.1f}
ku_decay: {decay.decay_score:.3f}
ku_freshness: {decay.label}
ku_age_days: {decay.age_days}"""
        else:
            decay_block = f"ku_quality: {source.quality_score:.1f}"

        tags_list = "\n".join(f"  - {t}" for t in (source.tags[:6] or [source.platform]))
        authors_list = "\n".join(f"  - {a}" for a in (source.authors[:3] or ["Unknown"]))

        return f"""---
title: "{source.title}"
aliases:
  - "{slug_title}"
tags:
{tags_list}
ku_source_id: "{source.id}"
ku_platform: {source.platform}
ku_url: "{source.url}"
{decay_block}
ku_authors:
{authors_list}
ku_compiled: {today}
ku_last_updated: {today}
---"""

    def _inject_wikilinks(self, body: str, existing_titles: list[str]) -> str:
        """
        Auto-inject [[wikilinks]] for existing article titles that appear
        as plain text in the body. Only first occurrence per title.
        """
        for title in existing_titles:
            if len(title) < 4:
                continue
            # Only link if not already a wikilink
            plain_pattern = re.compile(
                r'(?<!\[\[)' + re.escape(title) + r'(?!\]\])',
                re.IGNORECASE
            )
            if plain_pattern.search(body):
                body = plain_pattern.sub(f"[[{title}]]", body, count=1)
        return body

    def _find_relevant_links(self, text: str, existing_titles: list[str]) -> list[str]:
        """Find existing wiki titles that are relevant to this text."""
        text_lower = text.lower()
        matches = []
        for title in existing_titles:
            if any(word.lower() in text_lower for word in title.split() if len(word) > 3):
                matches.append(title)
        return matches[:8]

    @staticmethod
    def _slugify(title: str) -> str:
        """Convert title to a clean slug for aliases."""
        slug = title.lower()
        slug = re.sub(r"[^\w\s-]", "", slug)
        slug = re.sub(r"\s+", "-", slug.strip())
        return slug
