"""Model manager for code completion."""

from __future__ import annotations

import logging
import threading
import time
from collections import OrderedDict
from typing import Any, Dict, List, Optional

try:
    import torch
    from transformers import GPT2LMHeadModel, GPT2Tokenizer
except ImportError:  # pragma: no cover - handled at runtime
    torch = None
    GPT2LMHeadModel = None
    GPT2Tokenizer = None

logger = logging.getLogger(__name__)


class ModelManager:
    """Loads and serves GPT-2 code completions with lightweight caching."""

    def __init__(
        self,
        model_name: str = "gpt2",
        cache_size: int = 256,
        max_input_tokens: int = 512,
    ) -> None:
        self.model_name = model_name
        self.cache_size = cache_size
        self.max_input_tokens = max_input_tokens
        self._model = None
        self._tokenizer = None
        self._lock = threading.Lock()
        self._cache: "OrderedDict[str, str]" = OrderedDict()
        self._request_count = 0
        self._total_latency_ms = 0.0

    def _ensure_loaded(self) -> None:
        if self._model is not None and self._tokenizer is not None:
            return

        if GPT2LMHeadModel is None or GPT2Tokenizer is None or torch is None:
            raise RuntimeError("Model dependencies are not installed")

        with self._lock:
            if self._model is not None and self._tokenizer is not None:
                return

            logger.info("Loading model %s", self.model_name)
            self._tokenizer = GPT2Tokenizer.from_pretrained(self.model_name)
            if self._tokenizer.pad_token is None:
                self._tokenizer.pad_token = self._tokenizer.eos_token

            self._model = GPT2LMHeadModel.from_pretrained(self.model_name)
            self._model.eval()

            if torch.cuda.is_available():
                self._model.to("cuda")

    def _cache_get(self, key: str) -> Optional[str]:
        value = self._cache.get(key)
        if value is not None:
            self._cache.move_to_end(key)
        return value

    def _cache_set(self, key: str, value: str) -> None:
        self._cache[key] = value
        self._cache.move_to_end(key)
        if len(self._cache) > self.cache_size:
            self._cache.popitem(last=False)

    def complete(self, code: str, max_new_tokens: int = 64) -> Dict[str, Any]:
        """Generate a completion for a single code snippet."""
        if not isinstance(code, str) or not code.strip():
            raise ValueError("'code' must be a non-empty string")
        if max_new_tokens <= 0:
            raise ValueError("'max_new_tokens' must be greater than 0")

        self._ensure_loaded()
        assert self._model is not None and self._tokenizer is not None

        cache_key = f"{code}|{max_new_tokens}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return {
                "completion": cached,
                "latency_ms": 0.0,
                "cached": True,
                "model": self.model_name,
            }

        start = time.perf_counter()
        inputs = self._tokenizer(
            code,
            return_tensors="pt",
            truncation=True,
            max_length=self.max_input_tokens,
        )

        if torch is not None and torch.cuda.is_available():
            inputs = {k: v.to("cuda") for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self._model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=True,
                top_p=0.95,
                temperature=0.8,
                pad_token_id=self._tokenizer.eos_token_id,
            )

        generated_text = self._tokenizer.decode(outputs[0], skip_special_tokens=True)
        completion = generated_text[len(code) :].strip() or generated_text.strip()
        latency_ms = (time.perf_counter() - start) * 1000

        self._request_count += 1
        self._total_latency_ms += latency_ms
        self._cache_set(cache_key, completion)

        return {
            "completion": completion,
            "latency_ms": latency_ms,
            "cached": False,
            "model": self.model_name,
        }

    def batch_complete(self, codes: List[str], max_new_tokens: int = 64) -> List[Dict[str, Any]]:
        """Generate completions for multiple snippets."""
        if not isinstance(codes, list) or not codes:
            raise ValueError("'codes' must be a non-empty list of strings")

        for code in codes:
            if not isinstance(code, str) or not code.strip():
                raise ValueError("All code snippets must be non-empty strings")

        self._ensure_loaded()
        assert self._model is not None and self._tokenizer is not None

        start = time.perf_counter()
        tokenized = self._tokenizer(
            codes,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=self.max_input_tokens,
        )

        if torch is not None and torch.cuda.is_available():
            tokenized = {k: v.to("cuda") for k, v in tokenized.items()}

        with torch.no_grad():
            outputs = self._model.generate(
                **tokenized,
                max_new_tokens=max_new_tokens,
                do_sample=True,
                top_p=0.95,
                temperature=0.8,
                pad_token_id=self._tokenizer.eos_token_id,
            )

        decoded = self._tokenizer.batch_decode(outputs, skip_special_tokens=True)
        latency_ms = (time.perf_counter() - start) * 1000

        per_item_latency = latency_ms / len(codes)
        self._request_count += len(codes)
        self._total_latency_ms += latency_ms

        results: List[Dict[str, Any]] = []
        for prompt, text in zip(codes, decoded):
            completion = text[len(prompt) :].strip() or text.strip()
            self._cache_set(f"{prompt}|{max_new_tokens}", completion)
            results.append(
                {
                    "completion": completion,
                    "latency_ms": per_item_latency,
                    "cached": False,
                    "model": self.model_name,
                }
            )
        return results

    def get_metrics(self) -> Dict[str, float]:
        """Return model performance counters."""
        avg = self._total_latency_ms / self._request_count if self._request_count else 0.0
        return {
            "request_count": float(self._request_count),
            "average_latency_ms": avg,
            "cache_entries": float(len(self._cache)),
        }
