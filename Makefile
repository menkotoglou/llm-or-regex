# LLM or Regex? - benchmark harness for the PyCon Greece 2026 talk.
#
# Free, no API keys:
#   make setup            venv + deps (requirements-lock.txt has the exact versions behind the results)
#   make tables           rebuild every table in results/ from the committed per-item rows, offline
#   make dryrun           exercise every module with a fake LLM arm; writes to results-dryrun/, not results/
#   make wordlist         fetch the LDNOOBW English list for the regex arm (network)
#   make samples          rebuild data/samples/ from Civil Comments (network)
#   make local            regex + alt-profanity-check + own classifier on the 2017 samples, latency, determinism
#   make obfuscation      the spelling-tricks experiment, local arms
#   make identity ALL_ARMS="regex apc own:train-4k"    the identity-term experiment, local arms only
#
# Spends money (keys in the environment; every run is resumable, so finished items are never re-bought):
#   make llm              the LLM arms on the 2017 samples, latency, determinism
#   make handlabeled      every arm on surge-1k, obfuscation and identity
#   make extraction       the booking-request extraction bench
#   make identity         the identity-term experiment, every arm
#
# Offline, once the runs exist:
#   make cost cascade report      (make tables runs all three plus the identity and obfuscation tables)

# The four LLM arms behind the published numbers: a small and a frontier model from each of two vendors.
LLM_ARMS ?= llm:anthropic:claude-haiku-4-5-20251001 llm:anthropic:claude-opus-5 \
            llm:openai:gpt-5.4-mini llm:openai:gpt-6-astra
OWN      ?= own:train-4k
ALL_ARMS ?= regex apc $(OWN) $(LLM_ARMS)
SAMPLES  ?= balanced-2k natural-2k surge-1k
PY       ?= .venv/bin/python
WORKERS  ?= 8

arm_flags = $(foreach a,$(1),--arm $(a))

setup:
	python3 -m venv .venv && $(PY) -m pip install -q -U pip && $(PY) -m pip install -q -r requirements.txt

wordlist:
	./scripts/fetch_wordlist.sh

samples:
	$(PY) -m bench.data --source hf

local:
	$(PY) -m bench.run --sample balanced-2k --arm regex --arm apc --arm $(OWN) --workers 1
	$(PY) -m bench.run --sample natural-2k  --arm regex --arm apc --arm $(OWN) --workers 1
	$(PY) -m bench.latency --sample balanced-2k --arm regex --arm apc --arm $(OWN)
	$(PY) -m bench.determinism --sample balanced-2k --arm apc --runs 2 --workers 1
	$(MAKE) report

obfuscation:
	$(PY) scripts/make_obfuscation.py --base balanced-2k
	$(PY) -m bench.run --sample obfuscation --arm regex --arm apc --arm $(OWN) --workers 1
	$(PY) scripts/obfuscation_table.py

identity:
	$(PY) scripts/make_identity.py
	$(PY) -m bench.run --sample identity $(call arm_flags,$(ALL_ARMS)) --workers 4
	$(PY) scripts/identity_table.py

llm:
	$(PY) -m bench.run --sample balanced-2k $(call arm_flags,$(LLM_ARMS)) --workers $(WORKERS)
	$(PY) -m bench.run --sample natural-2k  $(call arm_flags,$(LLM_ARMS)) --workers $(WORKERS)
	$(PY) -m bench.latency --sample balanced-2k $(call arm_flags,$(LLM_ARMS))
	$(PY) -m bench.determinism --sample balanced-2k $(call arm_flags,$(LLM_ARMS)) --n 200 --runs 3 --workers $(WORKERS)

handlabeled:
	$(PY) -m bench.run --sample surge-1k    $(call arm_flags,$(ALL_ARMS)) --workers 4
	$(PY) -m bench.run --sample obfuscation $(call arm_flags,$(ALL_ARMS)) --workers 4
	$(PY) -m bench.run --sample identity    $(call arm_flags,$(ALL_ARMS)) --workers 4
	$(MAKE) report
	$(PY) scripts/obfuscation_table.py
	$(PY) scripts/identity_table.py

extraction:
	$(PY) scripts/make_extraction.py
	$(PY) -m bench.extract $(call arm_flags,regex $(LLM_ARMS)) --workers 6

cost:
	$(PY) -m bench.cost --sample natural-2k $(call arm_flags,$(ALL_ARMS))

cascade:
	$(foreach m,$(LLM_ARMS),$(PY) -m bench.cascade --sample natural-2k --llm $(m) --router $(OWN) &&) true

report:
	$(PY) -m bench.report $(call arm_flags,$(ALL_ARMS)) --samples $(SAMPLES)

# offline and free: every table from the committed per-item rows (all but extraction, see results/README.md)
tables: cost cascade report
	$(PY) scripts/obfuscation_table.py
	$(PY) scripts/identity_table.py

# no network, no money: every module with the fake arm, kept away from the committed results
dryrun: export BENCH_RESULTS = $(CURDIR)/results-dryrun
dryrun:
	$(PY) -m bench.run --sample balanced-2k --arm regex --arm apc --arm llm:fake:any --n 300 --workers 4
	$(PY) -m bench.latency --sample balanced-2k --arm regex --arm apc --arm llm:fake:any --n 100 --warmup 10
	$(PY) -m bench.determinism --sample balanced-2k --arm llm:fake:any --n 100 --runs 3
	$(PY) -m bench.report --arm regex --arm apc --arm llm:fake:any --samples balanced-2k

.PHONY: setup wordlist samples local obfuscation identity extraction llm handlabeled cost cascade report tables dryrun
