"""Four-layer governance controls for the Ola support capstone."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import ClassVar


class ToolAccessDeniedError(PermissionError):
    """Raised when an agent is given more tool access than its role permits."""


class RuntimeBudgetExceededError(ValueError):
    """Raised before CrewAI runs when a request exceeds the runtime budget."""

    def __init__(self, decision: "BudgetDecision"):
        super().__init__("Request rejected before execution because it exceeds the runtime budget.")
        self.decision = decision


@dataclass(frozen=True)
class BudgetDecision:
    accepted: bool
    input_tokens: int
    reserved_pipeline_tokens: int
    estimated_total_tokens: int
    max_input_tokens: int
    max_total_tokens: int
    estimated_cost_usd: float
    max_cost_usd: float
    reasons: tuple[str, ...]

    def to_dict(self) -> dict:
        value = asdict(self)
        value["reasons"] = list(self.reasons)
        return value


class LeastAutonomyPolicy:
    """Application-layer allowlist for every CrewAI role."""

    ALLOWED_TOOLS: ClassVar[dict[str, frozenset[str]]] = {
        "Policy Retrieval Specialist": frozenset({"search_support_policies"}),
        "Ticket Lookup Specialist": frozenset({"check_support_ticket_status"}),
        "Support Response Composer": frozenset(),
    }

    @classmethod
    def validate(cls, role: str, tool_names) -> None:
        requested = frozenset(tool_names)
        allowed = cls.ALLOWED_TOOLS.get(role)
        if allowed is None:
            raise ToolAccessDeniedError(f"Unknown agent role: {role}")
        forbidden = requested - allowed
        if forbidden:
            raise ToolAccessDeniedError(
                f"{role} cannot access: {', '.join(sorted(forbidden))}"
            )


class RuntimeBudget:
    """Conservative preflight token and reference-cost cap for one request."""

    def __init__(
        self,
        max_input_tokens: int = 256,
        reserved_pipeline_tokens: int = 768,
        max_total_tokens: int = 1024,
        reference_cost_per_1000_tokens_usd: float = 0.001,
        max_cost_usd: float = 0.001,
    ):
        self.max_input_tokens = max_input_tokens
        self.reserved_pipeline_tokens = reserved_pipeline_tokens
        self.max_total_tokens = max_total_tokens
        self.reference_cost_per_1000_tokens_usd = reference_cost_per_1000_tokens_usd
        self.max_cost_usd = max_cost_usd

    @staticmethod
    def estimate_tokens(text: str) -> int:
        # Input-size estimate only, not actual total framework token usage.
        # Include byte length so unbroken strings cannot count as one tiny input.
        return max(len(re.findall(r"\w+|[^\w\s]", text, flags=re.UNICODE)),
                   (len(text.encode('utf-8')) + 3) // 4)

    def inspect(self, text: str) -> BudgetDecision:
        input_tokens = self.estimate_tokens(text)
        total = input_tokens + self.reserved_pipeline_tokens
        cost = round(total / 1000 * self.reference_cost_per_1000_tokens_usd, 8)
        reasons = []
        if input_tokens > self.max_input_tokens:
            reasons.append("input_token_limit")
        if total > self.max_total_tokens:
            reasons.append("total_token_limit")
        if cost > self.max_cost_usd:
            reasons.append("reference_cost_limit")
        return BudgetDecision(
            accepted=not reasons,
            input_tokens=input_tokens,
            reserved_pipeline_tokens=self.reserved_pipeline_tokens,
            estimated_total_tokens=total,
            max_input_tokens=self.max_input_tokens,
            max_total_tokens=self.max_total_tokens,
            estimated_cost_usd=cost,
            max_cost_usd=self.max_cost_usd,
            reasons=tuple(reasons),
        )

    def enforce(self, text: str) -> BudgetDecision:
        decision = self.inspect(text)
        if not decision.accepted:
            raise RuntimeBudgetExceededError(decision)
        return decision


GOVERNANCE_SUMMARY = {
    "organization": {
        "rule": "Use fabricated records, minimize retained data, and require humans for real-world actions.",
        "implemented_by": ["dataset.py", "knowledge_base/", "request_logging.py"],
    },
    "application": {
        "rule": "Give each agent only its allowlisted tool and mask supported PII.",
        "implemented_by": ["LeastAutonomyPolicy", "guardrails.py"],
    },
    "model": {
        "rule": "Use approved deterministic local mocks with no API keys or runtime network.",
        "implemented_by": ["crew_workflow.py", "autogen_review.py"],
    },
    "runtime": {
        "rule": "Reject requests before execution when token or reference-cost limits are exceeded.",
        "implemented_by": ["RuntimeBudget"],
    },
}

RISK_CLASSIFICATION = {
    "level": "Medium",
    "justification": (
        "This is a customer-support ticket assistant: it handles operational records and can influence "
        "customer communication, but it cannot make payments, change tickets, issue refunds, or access "
        "real Ola systems. Privacy masking, grounded evidence, least-autonomy tool access, bounded review, "
        "and human ownership of real actions are therefore required."
    ),
}
