# Summary  (generated 2026-09-17 10:45, commit 80aadae, malformed policy = open)

| arm | P (balanced-2k) | R (balanced-2k) | F1 (balanced-2k) | P (natural-2k) | R (natural-2k) | F1 (natural-2k) | P (surge-1k) | R (surge-1k) | F1 (surge-1k) | p50 ms | p95 ms | p99 ms | EUR/1M | malformed | disagree@t0 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| regex | 0.802 | 0.093 | 0.167 | 0.273 | 0.115 | 0.161 | 0.873 | 0.248 | 0.386 | 0.1 | 0.6 | 0.7 | - | 0.0% | - |
| apc | 0.933 | 0.307 | 0.462 | 0.640 | 0.408 | 0.498 | 0.931 | 0.481 | 0.634 | 1.2 | 1.2 | 1.3 | - | 0.0% | 0.0% |
| own:train-4k | 0.776 | 0.772 | 0.774 | 0.239 | 0.764 | 0.364 | 0.805 | 0.683 | 0.739 | 0.6 | 0.9 | 1.0 | - | 0.0% | - |
| llm:anthropic:claude-haiku-4-5-20251001 | 0.850 | 0.449 | 0.588 | 0.390 | 0.522 | 0.447 | 0.998 | 0.922 | 0.959 | 676.0 | 930.6 | 1667.4 | - | 0.0% | 6.5% |
| llm:anthropic:claude-opus-5 | 0.840 | 0.552 | 0.666 | 0.366 | 0.643 | 0.467 | 0.994 | 0.960 | 0.977 | 1818.9 | 2785.1 | 3608.2 | - | 0.0% | 1.5% |
| llm:openai:gpt-5.4-mini | 0.845 | 0.611 | 0.709 | 0.312 | 0.618 | 0.415 | 0.984 | 0.952 | 0.968 | 624.1 | 811.7 | 990.3 | - | 0.0% | 5.5% |
| llm:openai:gpt-6-astra | 0.824 | 0.687 | 0.749 | 0.286 | 0.701 | 0.407 | 0.990 | 0.988 | 0.989 | 1652.2 | 3773.6 | 4911.9 | - | 0.0% | 4.5% |

Latency: concurrency 1, 50 warmup calls, same 200 items per arm. LLM latency includes the network from the measuring machine. Costs from real token counts x the dated price table in config/prices.toml.

apc: cold start import 2060 ms, first predict 6 ms, max RSS 188 MB, batch 81842 items/s; measured on macOS-26.5.2-arm64-arm-64bit-Mach-O.
