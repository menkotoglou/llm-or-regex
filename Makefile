# LLM or Regex? - benchmark harness for the PyCon Greece 2026 talk.
#
# Usage (in order):
#   make setup            venv + deps
#   make wordlist         LDNOOBW English list for the regex arm
#   make samples          balanced-2k + natural-2k + train-4k from Civil Comments (needs network)
#   make dryrun           every module with a fake LLM arm: no network, no money
#   make local            experiments 1-3 for regex + apc + own (no API cost)
#   make obfuscation      experiment 7
#   make extraction       slide 16: field extraction + invention rate   <- spends money
#   make identity         experiment 9
#   make llm              experiments 1-4 for the LLM arms          <- spends money
#   make handlabeled      the LLM arms on the hand-labelled sets     <- spends money
#   make cost             fill config/prices.toml first
#   make cascade          experiment 8, offline
#   make report           results/summary.md
#
# Set the model ids once:
LLM_SMALL    ?= llm:anthropic:claude-haiku-4-5-20251001
LLM_FRONTIER ?= llm:anthropic:claude-opus-5
LLM_ARMS     ?= $(LLM_SMALL) $(LLM_FRONTIER)
OWN          ?= own:train-4k
ALL_ARMS     := regex apc $(OWN) $(LLM_ARMS)
PY           ?= .venv/bin/python
WORKERS      ?= 8

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
	$(PY) -m bench.report --arm regex --arm apc --arm $(OWN)

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
	$(PY) -m bench.report $(call arm_flags,$(ALL_ARMS)) --samples surge-1k obfuscation
	$(PY) scripts/obfuscation_table.py
	$(PY) scripts/identity_table.py

extraction:
	$(PY) scripts/make_extraction.py
	$(PY) -m bench.extract $(call arm_flags,regex $(LLM_ARMS)) --workers 6

cost:
	$(PY) -m bench.cost --sample natural-2k $(call arm_flags,$(ALL_ARMS))

cascade:
	$(PY) -m bench.cascade --sample natural-2k --llm $(LLM_SMALL) --router $(OWN)
	$(PY) -m bench.cascade --sample natural-2k --llm $(LLM_FRONTIER) --router $(OWN)

report:
	$(PY) -m bench.report $(call arm_flags,$(ALL_ARMS))

# no network, no money: exercises every module with the fake arm
dryrun:
	$(PY) -m bench.run --sample balanced-2k --arm regex --arm apc --arm llm:fake:any --n 300 --workers 4
	$(PY) -m bench.latency --sample balanced-2k --arm regex --arm apc --arm llm:fake:any --n 100 --warmup 10
	$(PY) -m bench.determinism --sample balanced-2k --arm llm:fake:any --n 100 --runs 3
	$(PY) -m bench.report --arm regex --arm apc --arm llm:fake:any --samples balanced-2k

.PHONY: setup wordlist samples local obfuscation identity extraction llm handlabeled cost cascade report dryrun
