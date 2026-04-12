# ku-wiki — Karpathy-Style LLM Wiki Builder

> **"Obsidian is the IDE. The LLM is the programmer. The wiki is the codebase."**
> — Andrej Karpathy

[![pip install ku-wiki](https://img.shields.io/badge/pip%20install-ku--wiki-blue)](https://pypi.org/project/ku-wiki/)
[![Knowledge Universe API](https://img.shields.io/badge/Powered%20by-Knowledge%20Universe-purple)](https://vlsiddarth-knowledge-universe.hf.space)
[![MIT License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

---

## What this is

Karpathy described a system where you drop raw files into a folder and an LLM "compiles" them into a living, interlinked Wikipedia written in Markdown. The idea went viral. The implementation stayed manual.

**ku-wiki automates the ingestion.**

One command discovers the highest-quality sources on any topic, compiles them into Obsidian-ready wiki articles with `[[wikilinks]]`, and attaches a **Knowledge Decay Score** to every article — so you can see at a glance which knowledge is fresh and which is aging.

```bash
ku-wiki build "attention mechanism" --vault ~/MyObsidianVault
```

Output in Obsidian:

```markdown
---
title: "Attention mechanism"
ku_quality: 9.1
ku_decay: 0.847
ku_freshness: stale       ← 7.5 years old
ku_age_days: 2736
---

## What this is

The attention mechanism allows a neural network to weigh...
[[Multi-head attention]] runs this operation in parallel...
[[Transformer architecture]] is built entirely on attention...
```

---

## The gap Karpathy left open

Karpathy's system has one manual step: finding and clipping the right sources. He uses the Obsidian Web Clipper browser extension to manually save articles to `raw/`.

**We replaced that step** with the [Knowledge Universe API](https://vlsiddarth-knowledge-universe.hf.space) — a retrieval API that crawls 18 sources in parallel (arXiv, GitHub, Wikipedia, StackOverflow, HuggingFace, YouTube, PapersWithCode, and more) and returns results scored for quality, difficulty alignment, and **knowledge decay**.

The decay scoring is the key innovation. Karpathy's articles have no provenance — no way to know if a wiki note was written from a 2019 blog post or a 2025 paper. Every article ku-wiki generates carries `ku_freshness` metadata. Stale knowledge is visible in the graph.

---

## Install

```bash
pip install ku-wiki
```

Get a free Knowledge Universe API key (500 calls/month, no credit card):
```bash
curl -X POST "https://vlsiddarth-knowledge-universe.hf.space/v1/signup?email=you@email.com"
```

For LLM compilation, get an [Anthropic API key](https://console.anthropic.com/).
Without it, ku-wiki runs in **template mode** — still useful, just less polished prose.

---

## Quick start

```bash
# 1. Initialize a vault
ku-wiki init --vault ~/MyWiki
# → Creates wiki/, raw/, CLAUDE.md, index.md, .ku-wiki.toml

# 2. Build your first topic
export KU_API_KEY=ku_test_...
export ANTHROPIC_API_KEY=sk-ant-...
ku-wiki build "transformer architecture" --vault ~/MyWiki

# 3. Open ~/MyWiki in Obsidian → enable Graph View
# → See articles connected by [[wikilinks]] with freshness colors

# 4. Run weekly to stay current
ku-wiki update --vault ~/MyWiki
```

---

## Commands

### `ku-wiki build "topic"`

Discovers sources via KU API, compiles them into wiki articles, updates the index.

```bash
ku-wiki build "RAG retrieval augmented generation"
ku-wiki build "attention mechanism" --difficulty 4
ku-wiki build "LangChain streaming" --formats pdf,github,stackoverflow --overwrite
```

**What happens:**
1. Calls `/v1/discover` → 8-10 sources with decay scores
2. Calls `/v1/coverage` → warns if topic is sparse
3. For each source → Claude synthesizes a 200-400 word wiki article
4. YAML frontmatter includes `ku_quality`, `ku_decay`, `ku_freshness`, `ku_age_days`
5. Wikilinks auto-injected between all articles
6. `index.md` updated with freshness summary

### `ku-wiki update`

Checks all tracked topics for new sources. Generates a "What Changed This Week" digest note.

```bash
ku-wiki update
ku-wiki update --since-days 14
ku-wiki update --webhook https://hooks.slack.com/...
```

The digest note (`wiki/_what-changed-2026-04-12.md`) shows:
- New sources per topic
- Field velocity (🚀 fast-moving vs 📚 mature)
- Articles updated
- Coverage gaps to fill

### `ku-wiki watch`

Background daemon. Runs `update` on a schedule.

```bash
ku-wiki watch --interval weekly
ku-wiki watch --interval daily --webhook https://hooks.discord.com/...
```

### `ku-wiki status`

Vault statistics: article count, graph density, most-linked articles, tracked topics.

```bash
ku-wiki status
```

---

## The YAML frontmatter — what makes it different

Every compiled article carries KU metadata in its YAML frontmatter:

```yaml
---
title: "RLHF reward model training"
tags:
  - rlhf
  - alignment
  - fine-tuning
ku_source_id: "arxiv:2203.02155"
ku_platform: arxiv
ku_url: "https://arxiv.org/abs/2203.02155"
ku_quality: 8.9           ← quality score 0-10
ku_decay: 0.184           ← decay 0.0 (fresh) to 1.0 (stale)
ku_freshness: fresh       ← fresh | aging | stale
ku_age_days: 321          ← days since publication
ku_authors:
  - Ouyang, Long
  - Wu, Jeff
ku_compiled: 2026-04-12
ku_last_updated: 2026-04-12
---
```

With Obsidian's [Dataview plugin](https://github.com/blacksmithgu/obsidian-dataview), you can query this metadata:

```dataview
TABLE ku_freshness, ku_quality, ku_age_days
FROM "wiki"
WHERE ku_freshness = "stale"
SORT ku_quality DESC
```

→ Shows all stale articles sorted by quality — exactly the ones worth refreshing first.

---

## Knowledge decay scoring

The decay formula (from [Knowledge Universe](https://vlsiddarth-knowledge-universe.hf.space)):

```
decay = 1 - 0.5^(age_days / half_life)
```

Half-lives are tuned per platform:

| Platform | Half-life | Rationale |
|---|---|---|
| HuggingFace | 120 days | ML landscape changes monthly |
| GitHub | 180 days | Dependencies update constantly |
| YouTube | 270 days | Tutorials date quickly |
| Stack Overflow | 365 days | API answers age with versions |
| arXiv | 1,095 days | Research has longer shelf life |
| Wikipedia | 1,460 days | Actively maintained |
| Open Library | 1,825 days | Books revised rarely |

A `ku_decay` of 0.0 means perfectly fresh. 1.0 means fully decayed.
`ku_freshness: stale` means the source is past its expected useful lifetime.

---

## Architecture

```
Your Terminal
     │
     ▼ ku-wiki build "topic"
┌────────────────────────────────────────────┐
│              ku-wiki                       │
│                                            │
│  1. KUClient.discover()                    │
│     → POST /v1/discover                    │
│     → 8-10 sources + decay scores          │
│                                            │
│  2. KUClient.coverage()                    │
│     → GET /v1/coverage                     │
│     → warns if topic is sparse             │
│                                            │
│  3. WikiCompiler.compile(source)           │
│     → Claude API (or template fallback)    │
│     → synthesized Markdown article         │
│                                            │
│  4. VaultWriter.write_article()            │
│     → YAML frontmatter + body → .md file  │
│                                            │
│  5. WikilinkGraph.rebuild_links()          │
│     → [[wikilinks]] between all articles   │
│                                            │
│  6. VaultWriter.update_index()             │
│     → freshness summary in index.md        │
└────────────────────────────────────────────┘
     │
     ▼ vault/wiki/topic-slug.md
┌────────────────────────────────────────────┐
│              Obsidian                      │
│  Graph View: wikilink knowledge graph      │
│  Dataview: query by ku_freshness, quality  │
│  Search: full-text across all articles     │
└────────────────────────────────────────────┘
```

---

## Configuration

Create `.ku-wiki.toml` in your project root (or run `ku-wiki init`):

```toml
ku_api_key = "ku_test_..."
anthropic_api_key = "sk-ant-..."
vault_path = "~/MyObsidianVault"

default_difficulty = 3
default_formats = ["pdf", "github", "html", "video", "jupyter", "stackoverflow"]
max_results = 10

update_interval = "weekly"
webhook_url = "https://hooks.slack.com/..."  # optional
```

Environment variables override config:
- `KU_API_KEY` — Knowledge Universe API key
- `ANTHROPIC_API_KEY` — Claude API key
- `KU_WIKI_VAULT` — vault path

---

## Example: 30-second demo

```bash
$ pip install ku-wiki
$ export KU_API_KEY=ku_test_cfbc56bd98b115d51a099b30...
$ export ANTHROPIC_API_KEY=sk-ant-...

$ ku-wiki build "mixture of experts architecture" --vault ./my-wiki

╭─────────────────────────────────────────────────────────────╮
│ Building wiki for: mixture of experts architecture           │
│ Vault: ./my-wiki  │  Difficulty: 3  │  LLM: Claude API      │
╰─────────────────────────────────────────────────────────────╯

✓ Found 10 sources (cold 4821ms)
✓ Coverage: good (75%)

  Compiling articles... ━━━━━━━━━━━━━━━━━━━━━━ 100%

✅ Articles compiled     10
⏭  Articles skipped     0
🔗 Wikilinks injected   23
📁 Vault location       ./my-wiki

Done! Open ./my-wiki in Obsidian → Graph View to see the knowledge graph.
```

---

## The example vault

Clone this repo and open `example-vault/` in Obsidian to see what the output looks like with 3 pre-built articles:

- `wiki/attention-mechanism.md` — with decay metadata showing it's 7.5 years old
- `wiki/transformer-architecture.md` — [[wikilinks]] to attention and BERT
- `wiki/rag-retrieval-augmented-generation.md` — shows aging score

Enable Graph View in Obsidian to see the connections.

---

## Relation to Knowledge Universe API

This tool is a showcase of the [Knowledge Universe API](https://vlsiddarth-knowledge-universe.hf.space) — a free retrieval API that crawls 18 sources in parallel with knowledge decay scoring.

The API provides what manual clipping cannot: instant, scored, multi-platform source discovery. Free tier: 500 calls/month, no credit card.

API endpoints used:
- `POST /v1/discover` — sources for a topic with decay scores
- `POST /v1/diff` — what's new since N days ago
- `GET /v1/coverage` — how well-covered is a topic

---

## License

MIT. Clone, fork, use in your own projects.

Knowledge Universe API is free for developers.
GitHub: [VLSiddarth/Knowledge-Universe](https://github.com/VLSiddarth/Knowledge-Universe)

---

*Inspired by [Andrej Karpathy's wiki builder idea](https://twitter.com/karpathy). Built with [Knowledge Universe API](https://vlsiddarth-knowledge-universe.hf.space).*
