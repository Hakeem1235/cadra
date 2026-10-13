from __future__ import annotations

import time
from dataclasses import dataclass, field


TOKEN_COST_PER_1K = {
    "gemini-2.0-flash": {"input": 0.0001, "output": 0.0004},
    "gemini-1.5-flash": {"input": 0.000075, "output": 0.0003},
    "default": {"input": 0.0001, "output": 0.0004},
}


@dataclass
class ModelCall:
    model: str
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass
class DocUsed:
    document: str
    version: str


@dataclass
class TraceCollector:
    model_calls: list[ModelCall] = field(default_factory=list)
    tools_called: list[str] = field(default_factory=list)
    documents_used: list[DocUsed] = field(default_factory=list)
    _start: float = field(default_factory=time.perf_counter)

    def record_model(self, model: str, input_tokens: int, output_tokens: int):
        self.model_calls.append(ModelCall(model, input_tokens, output_tokens))

    def record_tool(self, name: str):
        if name not in self.tools_called:
            self.tools_called.append(name)

    def record_doc(self, document: str, version: str):
        entry = DocUsed(document, version)
        if entry not in self.documents_used:
            self.documents_used.append(entry)

    @property
    def cost_usd(self) -> float:
        total = 0.0
        for mc in self.model_calls:
            prices = TOKEN_COST_PER_1K.get(mc.model, TOKEN_COST_PER_1K["default"])
            total += mc.input_tokens * prices["input"] / 1000
            total += mc.output_tokens * prices["output"] / 1000
        return round(total, 6)

    @property
    def latency_ms(self) -> float:
        return round((time.perf_counter() - self._start) * 1000, 1)

    def to_dict(self) -> dict:
        return {
            "model_calls": [{"model": m.model, "input_tokens": m.input_tokens, "output_tokens": m.output_tokens} for m in self.model_calls],
            "tools_called": self.tools_called,
            "documents_used": [{"document": d.document, "version": d.version} for d in self.documents_used],
            "cost_usd": self.cost_usd,
            "latency_ms": self.latency_ms,
        }