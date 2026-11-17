# OWASP Top 10 for LLM Applications (2025 edition)

The OWASP Top 10 for LLM Applications is a standardised list of the most critical risk categories for applications built with Large Language Models.

| ID | Name | Short description |
|---|---|---|
| LLM01 | Prompt Injection | Malicious input that causes the LLM to ignore its system prompt or take unintended actions. |
| LLM02 | Sensitive Information Disclosure | The LLM leaks secrets, PII, or training data in its output. |
| LLM03 | Supply Chain | Compromised models, datasets, or dependencies introduce risk. |
| LLM04 | Data and Model Poisoning | Malicious data in training, fine-tuning, or embedding pipelines corrupts model behaviour. |
| LLM05 | Improper Output Handling | LLM output is executed, rendered, or stored without validation, enabling downstream attacks (XSS, SSRF, etc.). |
| LLM06 | Excessive Agency | The LLM is granted tool permissions broader than necessary; actions cannot be safely constrained. |
| LLM07 | System Prompt Leakage | Users can extract the system prompt, exposing business logic and constraints. |
| LLM08 | Vector and Embedding Weaknesses | RAG corpus can be poisoned, extracted, or manipulated; access control weak. |
| LLM09 | Misinformation | The model generates plausible but false information (hallucinations) that users may act on. |
| LLM10 | Unbounded Consumption | No rate limits, cost caps, or quota controls — denial-of-service or runaway cost. |

## Relation to hallucination detection

Hallucination detection is an **operational control for LLM09 (Misinformation)**. A dedicated claim-extraction + RAG-verification pipeline:
- Identifies where an LLM has produced a false or unsupported factual claim.
- Attaches an audit-trail annotation (supporting explainability / EU AI Act Article 13).
- Warns the human reviewer rather than silently passing the output downstream (supporting IIA Std 2310 "reliable information").

## Source

OWASP Foundation — [https://owasp.org/www-project-top-10-for-large-language-model-applications/](https://owasp.org/www-project-top-10-for-large-language-model-applications/)
