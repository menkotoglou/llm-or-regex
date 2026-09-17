"""The arms behind one interface.

An *arm* is anything that takes a piece of text and says toxic / not toxic.
Every arm returns the same `Prediction`, so the metrics, latency, cost and
cascade code never needs to know which arm produced a row.

Arm specs (what you pass on the command line):

    regex                        banned-word list, word-boundary match
    apc                          alt-profanity-check (LinearSVC, bag of words)
    own:<train-sample>           tf-idf + logistic regression trained on YOUR labels
                                 (e.g. own:train-4k, built by bench.data, disjoint from the eval samples)
    llm:anthropic:<model-id>     e.g. llm:anthropic:claude-haiku-4-5-20251001
    llm:openai:<model-id>        e.g. llm:openai:gpt-5.6-luna
    llm:fake:any                 no network, for dry runs of the pipeline
"""
from __future__ import annotations

import json
import os
import threading
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
WORDLIST = ROOT / "data" / "wordlists" / "en.txt"
PROMPT_FILE = ROOT / "prompts" / "moderation.txt"


@dataclass
class Prediction:
    item_id: str
    label: Optional[int]          # gold label, carried through for convenience
    pred: Optional[int]           # 1 toxic, 0 clean, None if malformed/error
    score: Optional[float] = None # probability-like score when the arm has one
    latency_ms: float = 0.0
    tokens_in: int = 0
    tokens_out: int = 0
    malformed: bool = False       # arm answered, but not in the agreed format
    error: Optional[str] = None   # arm did not answer at all (after retries)
    attempts: int = 1
    raw: str = ""                 # what the arm actually said, for the failure-mode slide
    meta: dict = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)


class Arm:
    name: str = "base"

    def predict(self, item_id: str, text: str, label: Optional[int]) -> Prediction:
        raise NotImplementedError

    def predict_batch(self, texts: list[str]) -> list[int]:
        """Optional. Only used for batch-throughput numbers."""
        raise NotImplementedError


# --------------------------------------------------------------------------- regex

class RegexArm(Arm):
    name = "regex"

    def __init__(self, wordlist: Path = WORDLIST):
        if not wordlist.exists():
            raise FileNotFoundError(
                f"{wordlist} missing. Run `make wordlist` (downloads the LDNOOBW English list)."
            )
        words = [w.strip() for w in wordlist.read_text(encoding="utf-8").splitlines()]
        words = [w for w in words if w and not w.startswith("#")]
        # longest first so multi-word phrases win over their prefixes
        words.sort(key=len, reverse=True)
        alternation = "|".join(re.escape(w) for w in words)
        self.pattern = re.compile(rf"\b(?:{alternation})\b", re.IGNORECASE)
        self.n_words = len(words)

    def complete_retrying(self, system: str, user: str) -> tuple[str, int, int]:
        """complete() under the same capability-discovery ladder predict() uses.

        complete() alone raises on the first unsupported parameter, because the flags are
        only ever flipped by the handler in _predict. Anything calling complete() directly
        (bench.extract) needs this wrapper or it fails on every single item.
        """
        last_err = None
        for attempt in range(1, self.max_retries + 1):
            try:
                return self.complete(system, user)
            except Exception as e:  # noqa: BLE001
                msg = str(e)
                last_err = msg
                low = msg.lower()
                if "temperature" in low and self._temperature_ok:
                    self._temperature_ok = False
                    continue
                if "thinking" in low and self._thinking_off_ok:
                    self._thinking_off_ok = False
                    continue
                if "reasoning_effort" in low and self._reasoning_effort:
                    self._reasoning_effort = "low" if self._reasoning_effort == "none" else None
                    continue
                if any(k in low for k in _RETRYABLE) and attempt < self.max_retries:
                    time.sleep(min(2 ** attempt, 30))
                    continue
                break
        raise RuntimeError(last_err or "unknown")

    def _meta(self) -> dict:
        m = {"model": self.model, "temperature_ok": self._temperature_ok}
        if self.provider == "anthropic":
            m["thinking_off"] = self._thinking_off_ok
        elif self.provider == "openai":
            m["reasoning_effort"] = self._reasoning_effort
            m["token_param"] = self._token_param
        return m

    def predict(self, item_id, text, label):
        t0 = time.perf_counter()
        hit = self.pattern.search(text)
        ms = (time.perf_counter() - t0) * 1000
        return Prediction(item_id, label, int(bool(hit)), score=float(bool(hit)),
                          latency_ms=ms, raw=hit.group(0) if hit else "")

    def predict_batch(self, texts):
        return [int(bool(self.pattern.search(t))) for t in texts]


# --------------------------------------------------------------------------- apc

class APCArm(Arm):
    name = "apc"

    def __init__(self, threshold: float = 0.5):
        from profanity_check import predict_prob  # import here so cold start is measurable elsewhere
        self._predict_prob = predict_prob
        self.threshold = threshold
        import importlib.metadata as md
        self.version = md.version("alt-profanity-check")

    def complete_retrying(self, system: str, user: str) -> tuple[str, int, int]:
        """complete() under the same capability-discovery ladder predict() uses.

        complete() alone raises on the first unsupported parameter, because the flags are
        only ever flipped by the handler in _predict. Anything calling complete() directly
        (bench.extract) needs this wrapper or it fails on every single item.
        """
        last_err = None
        for attempt in range(1, self.max_retries + 1):
            try:
                return self.complete(system, user)
            except Exception as e:  # noqa: BLE001
                msg = str(e)
                last_err = msg
                low = msg.lower()
                if "temperature" in low and self._temperature_ok:
                    self._temperature_ok = False
                    continue
                if "thinking" in low and self._thinking_off_ok:
                    self._thinking_off_ok = False
                    continue
                if "reasoning_effort" in low and self._reasoning_effort:
                    self._reasoning_effort = "low" if self._reasoning_effort == "none" else None
                    continue
                if any(k in low for k in _RETRYABLE) and attempt < self.max_retries:
                    time.sleep(min(2 ** attempt, 30))
                    continue
                break
        raise RuntimeError(last_err or "unknown")

    def _meta(self) -> dict:
        m = {"model": self.model, "temperature_ok": self._temperature_ok}
        if self.provider == "anthropic":
            m["thinking_off"] = self._thinking_off_ok
        elif self.provider == "openai":
            m["reasoning_effort"] = self._reasoning_effort
            m["token_param"] = self._token_param
        return m

    def predict(self, item_id, text, label):
        t0 = time.perf_counter()
        p = float(self._predict_prob([text])[0])
        ms = (time.perf_counter() - t0) * 1000
        return Prediction(item_id, label, int(p >= self.threshold), score=p, latency_ms=ms,
                          meta={"version": self.version})

    def predict_batch(self, texts):
        return [int(p >= self.threshold) for p in self._predict_prob(texts)]


# --------------------------------------------------------------------------- own

class OwnArm(Arm):
    """The 'you have a thousand labels from your own product' arm.
    Word + char n-gram tf-idf into logistic regression. Trains in about a second."""

    def __init__(self, train_sample: str, threshold: float = 0.5):
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.linear_model import LogisticRegression
        from sklearn.pipeline import make_pipeline, make_union
        from .data import load_sample
        df = load_sample(train_sample)
        self.name = f"own:{train_sample}"
        self.threshold = threshold
        self.n_train = len(df)
        self.pipe = make_pipeline(
            make_union(TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True),
                       TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=2, sublinear_tf=True)),
            LogisticRegression(C=4, max_iter=2000, class_weight="balanced"))
        t0 = time.perf_counter()
        self.pipe.fit(df["text"].values, df["label"].values)
        self.fit_seconds = time.perf_counter() - t0

    def complete_retrying(self, system: str, user: str) -> tuple[str, int, int]:
        """complete() under the same capability-discovery ladder predict() uses.

        complete() alone raises on the first unsupported parameter, because the flags are
        only ever flipped by the handler in _predict. Anything calling complete() directly
        (bench.extract) needs this wrapper or it fails on every single item.
        """
        last_err = None
        for attempt in range(1, self.max_retries + 1):
            try:
                return self.complete(system, user)
            except Exception as e:  # noqa: BLE001
                msg = str(e)
                last_err = msg
                low = msg.lower()
                if "temperature" in low and self._temperature_ok:
                    self._temperature_ok = False
                    continue
                if "thinking" in low and self._thinking_off_ok:
                    self._thinking_off_ok = False
                    continue
                if "reasoning_effort" in low and self._reasoning_effort:
                    self._reasoning_effort = "low" if self._reasoning_effort == "none" else None
                    continue
                if any(k in low for k in _RETRYABLE) and attempt < self.max_retries:
                    time.sleep(min(2 ** attempt, 30))
                    continue
                break
        raise RuntimeError(last_err or "unknown")

    def _meta(self) -> dict:
        m = {"model": self.model, "temperature_ok": self._temperature_ok}
        if self.provider == "anthropic":
            m["thinking_off"] = self._thinking_off_ok
        elif self.provider == "openai":
            m["reasoning_effort"] = self._reasoning_effort
            m["token_param"] = self._token_param
        return m

    def predict(self, item_id, text, label):
        t0 = time.perf_counter()
        p = float(self.pipe.predict_proba([text])[0, 1])
        ms = (time.perf_counter() - t0) * 1000
        return Prediction(item_id, label, int(p >= self.threshold), score=p, latency_ms=ms,
                          meta={"train": self.name, "n_train": self.n_train})

    def predict_batch(self, texts):
        return [int(p >= self.threshold) for p in self.pipe.predict_proba(texts)[:, 1]]


# --------------------------------------------------------------------------- llm

_JSON_OBJ = re.compile(r"\{.*?\}", re.S)
# A ceiling, not a target: well-behaved arms still answer in ~9 tokens. 24 was too tight for
# models that reason a little before answering -- they hit the cap and return empty content,
# which scores as "malformed" and fabricates a finding. Anthropic arms already run used 9-10
# tokens and never approached 24, so their results are unaffected by this change.
MAX_OUT = 256

_RETRYABLE = ("rate", "429", "overloaded", "529", "500", "502", "503", "504", "timeout", "timed out", "connection")


def parse_verdict(text: str) -> Optional[int]:
    """Return 1/0 from the model's JSON, or None if it did not follow the format."""
    m = _JSON_OBJ.search(text or "")
    if not m:
        return None
    try:
        obj = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    v = obj.get("toxic")
    if isinstance(v, bool):
        return int(v)
    if isinstance(v, str) and v.lower() in ("true", "false"):
        return int(v.lower() == "true")
    return None


class LLMArm(Arm):
    def __init__(self, provider: str, model: str, max_retries: int = 5, timeout: float = 60.0):
        self.provider, self.model = provider, model
        self.name = f"llm:{provider}:{model}"
        self.max_retries, self.timeout = max_retries, timeout
        self.prompt = PROMPT_FILE.read_text(encoding="utf-8")
        self.system, self.user_tmpl = self.prompt.split("---USER---", 1)
        self.system = self.system.replace("---SYSTEM---", "").strip()
        self.user_tmpl = self.user_tmpl.strip()
        self._temperature_ok = True
        self._thinking_off_ok = True   # Opus 5 / Sonnet 5 think by default: 24 output tokens is not enough
        self._reasoning_effort = "none"   # step down to "low" if a model rejects "none"; 24 tokens is the budget
        self._token_param = "max_tokens"   # reasoning models want max_completion_tokens; remember which
        self._probe_lock = threading.Lock()   # settle the flags on one call, not on N workers at once
        self._probed = False
        self._client = self._make_client()

    def _make_client(self):
        if self.provider == "anthropic":
            from anthropic import Anthropic
            return Anthropic(timeout=self.timeout, max_retries=0)
        if self.provider == "openai":
            from openai import OpenAI
            return OpenAI(timeout=self.timeout, max_retries=0)
        if self.provider == "fake":
            return None
        raise ValueError(f"unknown provider {self.provider!r}")

    # one call, no retry logic -> returns (text, tokens_in, tokens_out)
    def _call(self, text: str) -> tuple[str, int, int]:
        return self.complete(self.system, self.user_tmpl.replace("{text}", text))

    def complete(self, system: str, user: str) -> tuple[str, int, int]:
        """One provider call under the discovered capability flags. Reused by bench.extract."""
        if self.provider == "anthropic":
            kwargs = dict(model=self.model, max_tokens=MAX_OUT, system=system,
                          messages=[{"role": "user", "content": user}])
            if self._temperature_ok:
                kwargs["temperature"] = 0
            if self._thinking_off_ok:
                kwargs["thinking"] = {"type": "disabled"}
            r = self._client.messages.create(**kwargs)
            out = "".join(getattr(b, "text", "") for b in r.content)
            return out, r.usage.input_tokens, r.usage.output_tokens
        if self.provider == "openai":
            kwargs = dict(model=self.model,
                          messages=[{"role": "system", "content": system},
                                    {"role": "user", "content": user}])
            if self._temperature_ok:
                kwargs["temperature"] = 0
            if self._reasoning_effort:
                kwargs["reasoning_effort"] = self._reasoning_effort
            kwargs[self._token_param] = MAX_OUT
            try:
                r = self._client.chat.completions.create(**kwargs)
            except Exception as e:  # newer OpenAI models want max_completion_tokens -- switch once, not per call
                if "max_tokens" in str(e) and self._token_param == "max_tokens":
                    self._token_param = "max_completion_tokens"
                    kwargs.pop("max_tokens")
                    kwargs[self._token_param] = MAX_OUT
                    r = self._client.chat.completions.create(**kwargs)
                else:
                    raise
            out = r.choices[0].message.content or ""
            return out, r.usage.prompt_tokens, r.usage.completion_tokens
        # fake: deterministic-ish, occasionally malformed, no network
        time.sleep(0.005)
        text = user
        toxic = any(w in text.lower() for w in ("fuck", "shit", "idiot", "stupid", "kill", "hate"))
        if hash(text) % 97 == 0:
            return "Sure! This comment seems fine to me.", 120, 9
        return json.dumps({"toxic": toxic}), 120 + len(text) // 4, 6

    def complete_retrying(self, system: str, user: str) -> tuple[str, int, int]:
        """complete() under the same capability-discovery ladder predict() uses.

        complete() alone raises on the first unsupported parameter, because the flags are
        only ever flipped by the handler in _predict. Anything calling complete() directly
        (bench.extract) needs this wrapper or it fails on every single item.
        """
        last_err = None
        for attempt in range(1, self.max_retries + 1):
            try:
                return self.complete(system, user)
            except Exception as e:  # noqa: BLE001
                msg = str(e)
                last_err = msg
                low = msg.lower()
                if "temperature" in low and self._temperature_ok:
                    self._temperature_ok = False
                    continue
                if "thinking" in low and self._thinking_off_ok:
                    self._thinking_off_ok = False
                    continue
                if "reasoning_effort" in low and self._reasoning_effort:
                    self._reasoning_effort = "low" if self._reasoning_effort == "none" else None
                    continue
                if any(k in low for k in _RETRYABLE) and attempt < self.max_retries:
                    time.sleep(min(2 ** attempt, 30))
                    continue
                break
        raise RuntimeError(last_err or "unknown")

    def _meta(self) -> dict:
        m = {"model": self.model, "temperature_ok": self._temperature_ok}
        if self.provider == "anthropic":
            m["thinking_off"] = self._thinking_off_ok
        elif self.provider == "openai":
            m["reasoning_effort"] = self._reasoning_effort
            m["token_param"] = self._token_param
        return m

    def predict(self, item_id, text, label):
        # The capability flags above are discovered by failing once. Without this, every worker
        # in the pool discovers them independently and burns that item's retries doing it.
        if not self._probed:
            with self._probe_lock:
                if not self._probed:
                    try:
                        return self._predict(item_id, text, label)
                    finally:
                        self._probed = True
        return self._predict(item_id, text, label)

    def _predict(self, item_id, text, label):
        last_err, attempts = None, 0
        t0 = time.perf_counter()
        for attempt in range(1, self.max_retries + 1):
            attempts = attempt
            try:
                t_call = time.perf_counter()
                out, tin, tout = self._call(text)
                ms = (time.perf_counter() - t_call) * 1000
                pred = parse_verdict(out)
                return Prediction(item_id, label, pred, latency_ms=ms, tokens_in=tin, tokens_out=tout,
                                  malformed=pred is None, attempts=attempts, raw=out[:500],
                                  meta=self._meta())
            except Exception as e:  # noqa: BLE001
                msg = str(e)
                last_err = msg
                if "temperature" in msg.lower() and self._temperature_ok:
                    self._temperature_ok = False   # model rejects temperature; note it in meta
                    continue
                if "thinking" in msg.lower() and self._thinking_off_ok:
                    self._thinking_off_ok = False   # model rejects an explicit thinking block
                    continue
                if "reasoning_effort" in msg.lower() and self._reasoning_effort:
                    # "none" unsupported -> "low" (the documented minimum), then drop it entirely.
                    self._reasoning_effort = "low" if self._reasoning_effort == "none" else None
                    continue
                if any(k in msg.lower() for k in _RETRYABLE) and attempt < self.max_retries:
                    time.sleep(min(2 ** attempt, 30))
                    continue
                break
        ms = (time.perf_counter() - t0) * 1000
        return Prediction(item_id, label, None, latency_ms=ms, error=last_err[:300] if last_err else "unknown",
                          attempts=attempts, meta={"model": self.model})


# --------------------------------------------------------------------------- factory

def build_arm(spec: str) -> Arm:
    if spec == "regex":
        return RegexArm()
    if spec == "apc":
        return APCArm()
    if spec.startswith("llm:"):
        _, provider, model = spec.split(":", 2)
        return LLMArm(provider, model)
    if spec.startswith("own:"):
        return OwnArm(spec.split(":", 1)[1])
    raise ValueError(f"unknown arm spec {spec!r}")


def arm_slug(spec: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", spec)
