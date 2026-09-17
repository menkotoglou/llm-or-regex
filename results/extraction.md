# Extraction: accuracy on stated fields (invention rate on absent fields)

| field | regex | claude-haiku-4-5-20251001 | claude-opus-5 | gpt-5.4-mini | gpt-6-astra |
|---|---|---|---|---|---|
| time | 100% (0%) | 98% (0%) | 100% (0%) | 99% (1%) | 98% (0%) |
| party_size | 100% (0%) | 100% (0%) | 100% (0%) | 99% (0%) | 100% (0%) |
| date | 69% (0%) | 99% (0%) | 99% (0%) | 98% (1%) | 96% (0%) |
| cuisine | 46% (0%) | 87% (0%) | 83% (0%) | 89% (0%) | 59% (0%) |
| location | 0% (0%) | 54% (1%) | 70% (0%) | 77% (6%) | 95% (0%) |
| **invented a value that wasn't there** | **0%** | **0%** | **0%** | **2%** | **0%** |
