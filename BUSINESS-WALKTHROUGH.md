# Business walkthrough — Ola support agent

## What problem it solves

Support teams lose time searching policy documents, finding ticket details, and checking whether a draft reply has made up a promise. This demonstration puts those checks into one controlled support flow.

## What I would say in a presentation

“I built a support-assistant demonstration for Ola’s Business Operations and Customer Support domain. It answers only from a small fictional handbook and can look up only fabricated tickets. It helps an agent find the right information faster; it does not make decisions, approve money, or access real Ola systems.”

“When a customer asks a policy question, the system first removes supported sensitive formats from the working text and blocks suspicious instructions. It then searches the handbook, creates a response, and sends that response through a separate review step before showing it to the customer.”

“When the query contains a ticket ID, it retrieves the ticket’s status, estimated resolution hours, and a simple attention score. The score tells a human when the case deserves attention; it does not claim that a real SLA was breached.”

“The useful business point is control. The agent is allowed to retrieve and explain. A human keeps control of refunds, identity checks, escalations, and any change to a real customer record.”

## Three demonstrations to show

| Demo | What to ask | What it proves |
| --- | --- | --- |
| Policy question | “How often should outage progress updates be sent?” | The answer is pulled from the handbook and reviewed before it is returned. |
| Ticket lookup | “Please check ticket SUP-0014.” | The system retrieves fabricated record facts and recommends attention based on a clear formula. |
| Safe failure | “What is the weather in Mumbai today?” | It says it lacks policy information instead of inventing an answer. |

## Questions a reviewer may ask

| Question | Simple answer |
| --- | --- |
| Is this connected to Ola? | No. It is a local demonstration with fictional policies and fabricated tickets. |
| Why use multiple agents? | One finds policy information, one checks tickets, and one creates the reply. Separating those jobs makes the evidence easier to inspect. |
| How do you stop hallucinations? | The response must match retrieved evidence, then a second review team checks it again. If the handbook does not support an answer, it falls back. |
| What does memory do? | It remembers a ticket ID within one chat session, so a follow-up can work. A new session starts clean. |
| What does the escalation score mean? | It is a simple priority signal based on the stored escalation flag and ticket age. It helps a human decide where to look first. |
| Why are results perfect? | They are perfect only on a selected controlled test set. The report does not claim universal real-world accuracy. |
| What would you add for a real company? | Authentication, customer ownership checks, live data permissions, stronger privacy controls, real monitoring, and human approval for all actions. |

## Your role in this project

Your strongest contribution is the business design: the human boundaries, the risk of unsupported refund promises, the usefulness of a clear escalation signal, and why sales/support teams need quick policy retrieval. Explain those confidently. Do not overclaim that this is a production Ola system—it is not.
