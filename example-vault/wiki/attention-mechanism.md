---
title: "Attention mechanism"
aliases:
  - "attention-mechanism"
  - "self-attention"
tags:
  - transformers
  - deep-learning
  - nlp
  - neural-networks
ku_source_id: "arxiv:1706.03762"
ku_platform: arxiv
ku_url: "https://arxiv.org/abs/1706.03762"
ku_quality: 9.1
ku_decay: 0.847
ku_freshness: stale
ku_age_days: 2736
ku_authors:
  - Vaswani, Ashish
  - Shazeer, Noam
  - Parmar, Niki
ku_compiled: 2026-04-12
ku_last_updated: 2026-04-12
---

## What this is

The attention mechanism allows a neural network to weigh the importance of different input elements when computing a representation. Unlike RNNs that process sequences one token at a time, attention computes relationships between all pairs of positions simultaneously — enabling the model to "attend" to relevant context regardless of distance in the sequence.

## How it works

Given queries (Q), keys (K), and values (V) derived from the input, attention computes:

```
Attention(Q, K, V) = softmax(QK^T / √d_k) V
```

The scaling factor √d_k prevents the dot products from growing too large in high dimensions, which would push softmax into regions with vanishingly small gradients.

[[Multi-head attention]] runs this operation h times in parallel with different learned projections, then concatenates and projects the results. Each head can attend to different aspects of the input — one might capture syntactic relationships, another semantic ones.

[[Self-attention]] is the special case where Q, K, and V all come from the same sequence, letting the model relate every token to every other token.

## Why it matters

Attention solved the bottleneck problem in sequence-to-sequence models: the compressed context vector could not carry all information from long source sequences. With attention, the decoder can directly access any encoder state, weighted by relevance.

The [[transformer architecture]] built entirely on attention (removing recurrence) enabled parallel training across entire sequences — unlocking the scale that produced modern LLMs. Every major model from [[BERT]] to GPT-4 to [[Claude]] uses multi-head self-attention as its core operation.

## Related concepts

- [[Transformer architecture]] — the architecture built entirely on attention
- [[Multi-head attention]] — running attention in parallel across h heads
- [[Self-attention]] — attention within a single sequence
- [[BERT]] — bidirectional encoder using masked self-attention
- [[RAG retrieval augmented generation]] — retrieval systems that use attention-based embeddings

## Primary sources

- [Attention Is All You Need](https://arxiv.org/abs/1706.03762) — Vaswani et al. 2017 · *stale (7.5yr, decay=0.85)*
- [The Illustrated Transformer](https://jalammar.github.io/illustrated-transformer/) — Jay Alammar · *aging*
- [Distill: Attention and Augmented RNNs](https://distill.pub/2016/augmented-rnns/) — *aging*
