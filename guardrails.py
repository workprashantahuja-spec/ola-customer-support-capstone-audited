"""Deterministic input and output guardrails for the support assistant."""

from __future__ import annotations

import re
from dataclasses import dataclass

from crew_workflow import SupportResponse
from rag_config import FALLBACK_MESSAGE


PHONE_PATTERN = re.compile(
    r"(?<!\w)(?:\+?91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}(?!\w)"
)
CARD_LAST4_PATTERN = re.compile(
    r"(?i)(\b(?:card\s+)?(?:ending|ends)\s+(?:in\s+)?|"
    r"\b(?:card\s+)?last\s*4(?:\s+digits)?(?:\s+(?:are|is))?\s*)(\d{4})\b"
)
PAN_PATTERN = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b", re.IGNORECASE)
AADHAAR_PATTERN = re.compile(r"(?<!\d)\d{4}[\s-]?\d{4}[\s-]?\d{4}(?!\d)")
BANK_ACCOUNT_PATTERN = re.compile(
    r"(?i)(\b(?:bank\s+)?account(?:\s+(?:number|no\.?))?(?:\s+is)?\s*[:#-]?\s*)(\d{9,18})\b"
)

INJECTION_RULES = {
    "ignore_previous_instructions": re.compile(
        r"(?i)\bignore\s+(?:all\s+|any\s+|the\s+|your\s+)?(?:previous|prior)\s+instructions?\b"
    ),
    "reveal_system_prompt": re.compile(
        r"(?i)\b(?:reveal|show|print|repeat)\b.{0,40}\b(?:system|developer)\s+(?:prompt|message|instructions?)\b"
    ),
    "bypass_safety": re.compile(
        r"(?i)\b(?:bypass|disable|override|evade)\b.{0,30}\b(?:guardrails?|safety|security|rules?)\b"
    ),
    "impersonate_privileged_role": re.compile(
        r"(?i)\b(?:act|behave|respond)\s+as\s+(?:the\s+)?(?:system|developer|administrator)\b"
    ),
}


class PromptInjectionError(ValueError):
    def __init__(self, rule: str, safe_input: "SafeInput"):
        super().__init__(f"Blocked prompt-injection pattern: {rule}")
        self.rule = rule
        self.sanitized_text = safe_input.sanitized_text
        self.phone_numbers_masked = safe_input.phone_numbers_masked
        self.card_last4_masked = safe_input.card_last4_masked
        self.pan_masked = safe_input.pan_masked
        self.aadhaar_masked = safe_input.aadhaar_masked
        self.bank_accounts_masked = safe_input.bank_accounts_masked


class GroundednessError(ValueError):
    """Raised when the composed response does not match its tool evidence."""


@dataclass(frozen=True)
class SafeInput:
    sanitized_text: str
    phone_numbers_masked: int
    card_last4_masked: int
    pan_masked: int
    aadhaar_masked: int
    bank_accounts_masked: int

    @property
    def pii_was_masked(self):
        return bool(
            self.phone_numbers_masked or self.card_last4_masked or self.pan_masked
            or self.aadhaar_masked or self.bank_accounts_masked
        )


def _mask_card_last4(match: re.Match) -> str:
    return f"{match.group(1)}****"


def _mask_bank_account(match: re.Match) -> str:
    return f"{match.group(1)}[BANK_ACCOUNT]"


def mask_fixed_format_pii(text: str) -> SafeInput:
    """Mask the supported fixed-format identifiers before any pipeline use."""
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Input must be a nonempty string")
    phone_count = len(PHONE_PATTERN.findall(text))
    sanitized = PHONE_PATTERN.sub("[PHONE]", text)
    card_count = len(CARD_LAST4_PATTERN.findall(sanitized))
    sanitized = CARD_LAST4_PATTERN.sub(_mask_card_last4, sanitized)
    pan_count = len(PAN_PATTERN.findall(sanitized))
    sanitized = PAN_PATTERN.sub("[PAN]", sanitized)
    bank_count = len(BANK_ACCOUNT_PATTERN.findall(sanitized))
    sanitized = BANK_ACCOUNT_PATTERN.sub(_mask_bank_account, sanitized)
    aadhaar_count = len(AADHAAR_PATTERN.findall(sanitized))
    sanitized = AADHAAR_PATTERN.sub("[AADHAAR]", sanitized)
    return SafeInput(
        sanitized.strip(), phone_count, card_count, pan_count, aadhaar_count, bank_count
    )


def inspect_input(text: str) -> SafeInput:
    safe = mask_fixed_format_pii(text)
    for name, pattern in INJECTION_RULES.items():
        if pattern.search(safe.sanitized_text):
            raise PromptInjectionError(name, safe)
    return safe


def validate_grounded_output(response: SupportResponse, evidence: dict) -> SupportResponse:
    """Require every claim-bearing response to agree with its tool result."""
    response = SupportResponse.model_validate(response)
    if response.request_type == "policy":
        expected_fallback = bool(evidence.get("fallback"))
        if response.fallback_used != expected_fallback:
            raise GroundednessError("Policy fallback flag does not match retrieval evidence")
        if expected_fallback:
            if response.grounded or response.sources or response.answer != FALLBACK_MESSAGE:
                raise GroundednessError("Fallback response contains an unsupported policy claim")
            return response
        if not response.grounded:
            raise GroundednessError("Supported policy evidence was marked ungrounded")
        if response.answer != evidence.get("answer"):
            raise GroundednessError("Policy answer differs from the retrieved evidence")
        if response.sources != evidence.get("sources") or not response.sources:
            raise GroundednessError("Policy sources are missing or changed")
        if not all(source.startswith("knowledge_base/") for source in response.sources):
            raise GroundednessError("Policy source is outside the approved knowledge base")
        return response

    required_ticket = {
        key: evidence.get(key)
        for key in (
            "record_id", "status", "resolution_time_hours", "days_since_created",
            "escalated", "escalation_score", "human_attention_recommended",
        )
    }
    if response.ticket is None or response.ticket.model_dump() != required_ticket:
        raise GroundednessError("Ticket details differ from the lookup evidence")
    if not response.grounded or response.fallback_used:
        raise GroundednessError("Ticket response has inconsistent grounding flags")
    if response.sources != ["fabricated_support_tickets"]:
        raise GroundednessError("Ticket response has an unapproved source")
    from autogen_review import _canonical_ticket_answer
    if response.answer != _canonical_ticket_answer(evidence):
        raise GroundednessError("Ticket answer differs from the lookup evidence")
    return response
