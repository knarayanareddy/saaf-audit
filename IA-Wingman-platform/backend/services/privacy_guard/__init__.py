"""Privacy Guard — deterministic GDPR data-minimisation for fieldwork datasets.

Ported and trimmed from the SAAF GDPR-AI-Audit-Agent. Pure regex + HMAC + hash
chain; no AI. Detects PII, classifies each field Required/Optional/Excessive per
audit purpose, maps a GDPR legal basis, masks or pseudonymises per role, and
emits a tamper-evident audit trail. It produces a view + a trail — it writes
nothing into the RACM spine.
"""
