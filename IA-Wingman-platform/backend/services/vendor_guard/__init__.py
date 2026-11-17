"""Vendor Guard — third-party (vendor) risk assessment fieldwork agent.

Ported from the SAAF Vendor_Guard hackathon project and adapted to the IA
Wingman doctrine. Assesses uploaded vendor documents against a fixed library of
eight curated EU/NL frameworks (ISO 27001, NIS2, CBW, DORA, BIO2, EU AI Act,
ALTAI, EC Ethics), grouped into four specialist assessors. Framework
applicability is deterministic (security + resilience always; AI-trust only for
AI vendors; gov baseline only for Dutch-government vendors). The RAG scorecard,
status/severity normalisation and gap->risk mapping are deterministic; the
specialist assessments and the audit memo are the opt-in AI steps. Critical/High
gaps are proposed into the RACM spine as risks — proposals only.
"""
