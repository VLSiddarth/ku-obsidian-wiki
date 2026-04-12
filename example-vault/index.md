---
title: Knowledge Universe Wiki — Index
last_updated: 2026-04-12
---

# Knowledge Universe Wiki

> Built with [ku-wiki](https://github.com/VLSiddarth/ku-obsidian-wiki) · Powered by [Knowledge Universe API](https://vlsiddarth-knowledge-universe.hf.space)
> 3 articles · Updated 2026-04-12

## Knowledge freshness

- 🟢 Fresh (< 6 months): **0** articles
- 🟡 Aging (6-18 months): **1** article
- 🔴 Stale (> 18 months): **2** articles ← *run `ku-wiki update` to refresh*

## All articles

- 🔴 [[Attention mechanism]] · q=9.1 · *stale*
- 🟡 [[RAG retrieval augmented generation]] · q=8.7 · *aging*
- 🔴 [[Transformer architecture]] · q=9.4 · *stale*

---

## Commands

```bash
# Add a new topic
ku-wiki build "agentic workflows"

# Check for new sources (weekly)
ku-wiki update

# See vault stats
ku-wiki status
```

## What this is

This is a Karpathy-style personal knowledge wiki.
The LLM is the compiler. Knowledge Universe is the ingestion layer.
Obsidian is the IDE. This wiki is the living codebase.

Each article carries `ku_freshness` metadata — you can see at a glance
which knowledge is current and which needs refreshing.
