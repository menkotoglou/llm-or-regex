# Summary  (generated 2026-09-17 08:10, commit 2265dda, malformed policy = drop)

| arm | P (surge-1k) | R (surge-1k) | F1 (surge-1k) | p50 ms | p95 ms | p99 ms | EUR/1M | malformed | disagree@t0 |
|---|---|---|---|---|---|---|---|---|---|
| llm:anthropic:claude-haiku-4-5-20251001 | 0.998 | 0.922 | 0.959 | 676.0 | 930.6 | 1667.4 | - | 0.0% | 6.5% |
| llm:anthropic:claude-opus-5 | 0.994 | 0.960 | 0.977 | 1818.9 | 2785.1 | 3608.2 | - | 0.0% | 1.5% |

Latency: concurrency 1, 50 warmup calls, same 200 items per arm. LLM latency includes the network from the measuring machine. Costs from real token counts x the dated price table in config/prices.toml.
