---
title: "RAG retrieval augmented generation"
aliases:
  - "rag-retrieval-augmented-generation"
  - "RAG"
  - "retrieval augmented generation"
tags:
  - rag
  - llm
  - production
  - vector-search
ku_source_id: "arxiv:2005.11401"
ku_platform: arxiv
ku_url: "https://arxiv.org/abs/2005.11401"
ku_quality: 8.7
ku_decay: 0.612
ku_freshness: aging
ku_age_days: 712
ku_authors:
  - Lewis, Patrick
  - Perez, Ethan
ku_compiled: 2026-04-12
ku_last_updated: 2026-04-12
---

## What this is

Retrieval-Augmented Generation (RAG) augments an LLM's generation by first retrieving relevant documents from an external knowledge base and injecting them into the context. The LLM generates answers conditioned on both the query and the retrieved passages, grounding responses in verifiable sources rather than parametric memory alone.

## How it works

A RAG pipeline has two main components:

**Retrieval:** A query is encoded into a vector embedding and compared (usually via cosine similarity) against a pre-indexed corpus. The top-k most similar chunks are retrieved. Common retrievers include BM25 (sparse), FAISS (dense), or hybrid approaches that combine both.

**Generation:** The retrieved chunks are inserted into the LLM's context window, typically as: `Context: {chunks}\n\nQuestion: {query}\n\nAnswer:`. The LLM generates a response conditioned on this augmented input.

The [[attention mechanism]] in the underlying transformer attends over both the query and retrieved context simultaneously, allowing the model to synthesize across sources.

## Why it matters

RAG addresses two critical limitations of parametric LLMs: knowledge cutoff (static training data) and hallucination (confabulation when uncertain). By retrieving from a live knowledge base, RAG can answer questions about recent events and cite specific sources.

The silent failure mode: cosine similarity has no concept of time. A retrieved chunk from 2021 ranks identically to one from 2025. [[Knowledge decay scoring]] addresses this by penalizing stale sources before retrieval.

Production RAG systems at scale use [[vector databases]] like Pinecone, Weaviate, or pgvector for approximate nearest-neighbor search across millions of embeddings.

## Related concepts

- [[Attention mechanism]] — the core operation that processes retrieved context
- [[Vector databases]] — the storage layer for RAG embeddings
- [[Knowledge decay scoring]] — freshness scoring for retrieved sources
- [[Agentic workflows]] — multi-step reasoning that uses RAG as one tool
- [[LangChain]] — popular framework for building RAG pipelines

## Primary sources

- [Retrieval-Augmented Generation for Knowledge-Intensive NLP](https://arxiv.org/abs/2005.11401) — Lewis et al. · *aging (decay=0.61)*
- [Knowledge Universe API](https://vlsiddarth-knowledge-universe.hf.space) — decay-scored source discovery for RAG · *fresh*
- [LangChain RAG Tutorial](https://python.langchain.com/docs/use_cases/question_answering/) — *aging*
