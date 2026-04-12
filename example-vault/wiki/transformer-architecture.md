---
title: "Transformer architecture"
aliases:
  - "transformer-architecture"
  - "transformer"
tags:
  - transformers
  - deep-learning
  - nlp
  - architecture
ku_source_id: "arxiv:1706.03762"
ku_platform: arxiv
ku_url: "https://arxiv.org/abs/1706.03762"
ku_quality: 9.4
ku_decay: 0.847
ku_freshness: stale
ku_age_days: 2736
ku_authors:
  - Vaswani, Ashish
  - Shazeer, Noam
ku_compiled: 2026-04-12
ku_last_updated: 2026-04-12
---

## What this is

The transformer is a neural network architecture that uses [[attention mechanism]] exclusively — no recurrence, no convolution. Introduced in "Attention Is All You Need" (2017), it became the dominant architecture for NLP and has since spread to vision, audio, code, and protein folding.

## How it works

A transformer encoder consists of stacked layers, each containing:

1. **[[Multi-head attention]]** — relates each token to every other token via learned Q, K, V projections
2. **Feed-forward network** — two linear layers with a ReLU activation, applied independently to each position
3. **Layer normalization + residual connections** — after each sub-layer, enabling stable training of deep networks

The decoder adds cross-attention layers that attend to the encoder's output, enabling sequence-to-sequence tasks like translation.

Positional encodings (sinusoidal or learned) inject position information since attention is inherently permutation-invariant.

Training is embarrassingly parallel — unlike RNNs, all positions are processed simultaneously. This enabled training on dataset scales impossible with recurrent models.

## Why it matters

The transformer unlocked modern large language models. GPT, [[BERT]], T5, PaLM, LLaMA, and [[Claude]] are all transformer variants. Scaling transformers with more parameters and data produced emergent capabilities: in-context learning, chain-of-thought reasoning, and instruction following.

For [[RAG retrieval augmented generation]], transformers provide the embedding model that encodes both queries and documents into the same vector space.

The "bitter lesson" (Sutton): architectures that scale with compute beat hand-engineered inductive biases. Transformers scale cleanly with data and parameters — attention becomes more powerful as the key-value store grows.

## Related concepts

- [[Attention mechanism]] — the core operation, runs multiple times per layer
- [[Multi-head attention]] — the parallel attention variant used in transformers
- [[BERT]] — bidirectional transformer encoder pre-trained with MLM
- [[RAG retrieval augmented generation]] — retrieval systems built on transformer embeddings
- [[Mixture of experts]] — sparse transformer variant for parameter efficiency

## Primary sources

- [Attention Is All You Need](https://arxiv.org/abs/1706.03762) — Vaswani et al. 2017 · *stale (7.5yr)*
- [The Illustrated Transformer](https://jalammar.github.io/illustrated-transformer/) — Jay Alammar · *aging*
- [A Survey of Graph Transformers](https://arxiv.org/abs/2502.16533) — *fresh (2025)*
