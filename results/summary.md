# Summary  (generated 2026-09-16 23:38, commit dc770ec, malformed policy = open)

| arm | P (balanced-2k) | R (balanced-2k) | F1 (balanced-2k) | P (natural-2k) | R (natural-2k) | F1 (natural-2k) | P (surge-1k) | R (surge-1k) | F1 (surge-1k) | p50 ms | p95 ms | p99 ms | EUR/1M | malformed | disagree@t0 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| regex | 0.802 | 0.093 | 0.167 | 0.273 | 0.115 | 0.161 | 0.873 | 0.248 | 0.386 | 0.1 | 0.6 | 0.7 | - | 0.0% | - |
| apc | 0.933 | 0.307 | 0.462 | 0.640 | 0.408 | 0.498 | 0.931 | 0.481 | 0.634 | 1.2 | 1.2 | 1.3 | - | 0.0% | 0.0% |
| own:train-4k | 0.776 | 0.772 | 0.774 | 0.239 | 0.764 | 0.364 | 0.805 | 0.683 | 0.739 | 0.6 | 0.9 | 1.0 | - | 0.0% | - |

Latency: concurrency 1, 50 warmup calls, same 200 items per arm. LLM latency includes the network from the measuring machine. Costs from real token counts x the dated price table in config/prices.toml.

apc: cold start import 2060 ms, first predict 6 ms, max RSS 188 MB, batch 81842 items/s; measured on macOS-26.5.2-arm64-arm-64bit-Mach-O.
