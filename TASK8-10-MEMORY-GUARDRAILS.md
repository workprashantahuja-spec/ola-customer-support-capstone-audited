# Tasks 8 and 10 — Session memory and guardrails

## What this portion adds

`session_service.py` gives each conversation its own LangChain `InMemoryChatMessageHistory`. If a customer first asks about `SUP-0014` and then asks “What is its status?”, the second turn finds `SUP-0014` only inside that same session. A different session receives a request for the missing ticket ID, proving that one customer's context is not copied into another conversation.

`guardrails.py` adds checks before and after CrewAI runs:

| Check | What happens |
| --- | --- |
| Phone masking | A supported Indian phone format such as `+91 98765 43210` becomes `[PHONE]`. |
| Payment-card last-4 masking | A phrase such as “card ends in 4242” becomes “card ends in ****”. |
| PAN masking | A PAN such as `ABCDE1234F` becomes `[PAN]`. |
| Aadhaar masking | A 12-digit Aadhaar number, including spaced or hyphenated formats, becomes `[AADHAAR]`. |
| Labelled bank-account masking | A 9–18 digit number following “bank account number” becomes `[BANK_ACCOUNT]`. |
| Prompt-injection detection | Attempts to ignore instructions, reveal system prompts, bypass safeguards, or impersonate privileged roles are blocked before CrewAI. |
| Output groundedness | The composed policy or ticket response must match the actual tool evidence. Changed claims or sources are rejected. |

Only fixed-format phone numbers, explicit payment-card-last-4 phrases, PANs, Aadhaar numbers, and labelled bank-account numbers are masked. Names, addresses, and arbitrary free text are not claimed as reliably detected; all demonstrations use fabricated values.

## Demonstrations recorded

`verify_portion5.py` records:

1. Two turns in one session that retain `SUP-0014`.
2. The same follow-up in a fresh session that correctly asks for a ticket ID.
3. Phone, card-last-4, PAN, Aadhaar, and labelled bank-account masking before CrewAI and memory.
4. A deliberate prompt injection blocked before CrewAI.
5. A deliberate unsupported output rejected by the groundedness guardrail.

Run:

```powershell
python verify_portion5.py
python -m unittest test_memory_guardrails.py
```

The complete execution record is written to `transcripts/portion5_evidence.json`.
