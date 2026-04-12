"""
ku_client.py — Knowledge Universe API client for wiki builder.

Wraps three endpoints:
  /v1/discover  — find sources for a topic
  /v1/diff      — what changed since N days ago
  /v1/coverage  — how well-covered is a topic
"""

from __future__ import annotations

import httpx
from dataclasses import dataclass, field
from typing import Optional


KU_BASE = "https://vlsiddarth-knowledge-universe.hf.space"


# ─── Data models ──────────────────────────────────────────────────────────────

@dataclass
class KUDecay:
    decay_score: float
    freshness_score: float
    label: str          # "fresh" | "aging" | "stale" | "unknown"
    age_days: int
    half_life_days: Optional[int] = None


@dataclass
class KUSource:
    id: str
    title: str
    url: str
    platform: str
    quality_score: float
    summary: str
    difficulty: int
    formats: list[str]
    decay: Optional[KUDecay] = None
    authors: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)


@dataclass
class DiscoverResult:
    topic: str
    total_found: int
    processing_time_ms: float
    cache_hit: bool
    sources: list[KUSource]
    coverage_confidence: float


@dataclass
class DiffResult:
    topic: str
    since_days: int
    new_sources: list[KUSource]
    established_sources: list[KUSource]
    field_velocity: str     # "fast-moving" | "active" | "stable" | "mature"
    new_count: int
    established_count: int


@dataclass
class CoverageResult:
    topic: str
    overall_score: float
    overall_label: str      # "excellent" | "good" | "sparse" | "poor"
    total_sources: int
    gaps: list[str]
    recommendation: str
    format_coverage: dict
    freshness_distribution: dict


# ─── Client ───────────────────────────────────────────────────────────────────

class KUClient:
    """
    Knowledge Universe API client.

    Usage:
        client = KUClient(api_key="ku_test_...")
        result = client.discover("attention mechanism", difficulty=3)
        for source in result.sources:
            print(source.title, source.decay.label)
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = KU_BASE,
        timeout: float = 45.0,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self._headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json",
        }
        self._timeout = timeout

    def _parse_source(self, raw: dict, decay_map: dict) -> KUSource:
        src_id = raw.get("id", "")
        decay_raw = decay_map.get(src_id, {})

        decay = None
        if decay_raw:
            decay = KUDecay(
                decay_score=decay_raw.get("decay_score", 0.0),
                freshness_score=1.0 - decay_raw.get("decay_score", 0.0),
                label=decay_raw.get("label", "unknown"),
                age_days=int(decay_raw.get("age_days", -1)),
                half_life_days=decay_raw.get("half_life_days"),
            )

        return KUSource(
            id=src_id,
            title=raw.get("title", "Untitled"),
            url=raw.get("url", ""),
            platform=raw.get("source_platform", "unknown"),
            quality_score=float(raw.get("quality_score", 0.0)),
            summary=raw.get("summary", ""),
            difficulty=int(raw.get("difficulty", 3)),
            formats=raw.get("formats", []),
            decay=decay,
            authors=raw.get("authors", []),
            tags=raw.get("tags", []),
        )

    def discover(
        self,
        topic: str,
        difficulty: int = 3,
        formats: Optional[list[str]] = None,
        max_results: int = 10,
    ) -> DiscoverResult:
        """
        Discover high-quality sources for a topic.
        Returns sources with decay scores attached.
        """
        payload = {
            "topic": topic,
            "difficulty": difficulty,
            "formats": formats or ["pdf", "github", "html", "video", "jupyter", "stackoverflow"],
            "max_results": max_results,
        }
        with httpx.Client(headers=self._headers, timeout=self._timeout) as client:
            resp = client.post(f"{self.base_url}/v1/discover", json=payload)
            resp.raise_for_status()
            data = resp.json()

        decay_map = data.get("decay_scores", {})
        sources = [
            self._parse_source(s, decay_map)
            for s in data.get("sources", [])
        ]

        return DiscoverResult(
            topic=topic,
            total_found=data.get("total_found", len(sources)),
            processing_time_ms=data.get("processing_time_ms", 0.0),
            cache_hit=data.get("cache_hit", False),
            sources=sources,
            coverage_confidence=data.get("coverage_confidence", 0.0),
        )

    def diff(
        self,
        topic: str,
        since_days: int = 7,
        difficulty: int = 3,
    ) -> DiffResult:
        """
        Get what's new vs established for a topic.
        Use for weekly update runs.
        """
        payload = {
            "topic": topic,
            "since_days": since_days,
            "difficulty": difficulty,
        }
        try:
            with httpx.Client(headers=self._headers, timeout=self._timeout) as client:
                resp = client.post(f"{self.base_url}/v1/diff", json=payload)
                resp.raise_for_status()
                data = resp.json()

            new_sources = [self._parse_source(s, {}) for s in data.get("new_sources", [])]
            established = [self._parse_source(s, {}) for s in data.get("established_sources", [])]

            return DiffResult(
                topic=topic,
                since_days=since_days,
                new_sources=new_sources,
                established_sources=established,
                field_velocity=data.get("field_velocity", "unknown"),
                new_count=data.get("new_count", len(new_sources)),
                established_count=data.get("established_count", len(established)),
            )
        except Exception:
            # /v1/diff may not be deployed yet — fall back gracefully
            result = self.discover(topic, difficulty=difficulty)
            return DiffResult(
                topic=topic,
                since_days=since_days,
                new_sources=[s for s in result.sources if s.decay and s.decay.age_days >= 0 and s.decay.age_days <= since_days],
                established_sources=[s for s in result.sources if not (s.decay and s.decay.age_days >= 0 and s.decay.age_days <= since_days)],
                field_velocity="unknown",
                new_count=0,
                established_count=len(result.sources),
            )

    def coverage(self, topic: str, difficulty: int = 3) -> CoverageResult:
        """
        Get a coverage report: how well does KU cover this topic?
        """
        try:
            with httpx.Client(headers=self._headers, timeout=self._timeout) as client:
                resp = client.get(
                    f"{self.base_url}/v1/coverage",
                    params={"topic": topic, "difficulty": difficulty},
                )
                resp.raise_for_status()
                data = resp.json()

            return CoverageResult(
                topic=topic,
                overall_score=data.get("overall_score", 0.0),
                overall_label=data.get("overall_label", "unknown"),
                total_sources=data.get("total_sources", 0),
                gaps=data.get("gaps", []),
                recommendation=data.get("recommendation", ""),
                format_coverage=data.get("format_coverage", {}),
                freshness_distribution=data.get("freshness_distribution", {}),
            )
        except Exception:
            # /v1/coverage may not be deployed yet — estimate from discover
            result = self.discover(topic, difficulty=difficulty)
            n = len(result.sources)
            score = min(1.0, n / 8.0)
            label = "excellent" if score >= 0.75 else "good" if score >= 0.5 else "sparse" if score >= 0.3 else "poor"
            return CoverageResult(
                topic=topic,
                overall_score=round(score, 2),
                overall_label=label,
                total_sources=n,
                gaps=[] if n >= 6 else [f"only {n} sources found — topic may be niche"],
                recommendation=f"{label.capitalize()} coverage for '{topic}'.",
                format_coverage={},
                freshness_distribution={},
            )
