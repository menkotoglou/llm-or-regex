# Summary  (generated 2026-09-16 20:09, commit uncommitted, malformed policy = open)

| arm | P (surge-1k) | R (surge-1k) | F1 (surge-1k) | P (obfuscation) | R (obfuscation) | F1 (obfuscation) | p50 ms | p95 ms | p99 ms | EUR/1M | malformed | disagree@t0 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| regex | 0.873 | 0.248 | 0.386 | 1.000 | 0.242 | 0.390 | 0.1 | 0.4 | 0.8 | - | 0.0% | - |
| apc | 0.931 | 0.481 | 0.634 | 1.000 | 0.431 | 0.603 | 2.6 | 3.2 | 3.7 | - | 0.0% | 0.0% |

Latency: concurrency 1, 50 warmup calls, same 200 items per arm. LLM latency includes the network from the measuring machine. Costs from real token counts x the dated price table in config/prices.toml.

apc: cold start import 1076 ms, first predict 11 ms, max RSS 156 MB, batch 60019 items/s; measured on Linux-6.18.44-fc-v33-x86_64-with-glibc2.39.
