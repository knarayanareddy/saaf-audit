# OWASP LLM Top 10 Audit Report

**Target:** `.`
**Date:** 2026-03-24 14:18 UTC

## Summary

This audit tool itself has moderate exposure across several OWASP LLM controls. As an agent that calls the Claude API with user-supplied content, it faces prompt injection risks. The collector reads arbitrary filesystem paths without sandboxing. Output handling trusts the LLM response JSON without strict schema validation. The tool has limited agency (no write operations beyond report files), which is good. Supply chain risk is low given minimal dependencies.

## Scorecard

| Control | Name | Status |
|---------|------|--------|
| LLM01 | Prompt Injection | **WARN** |
| LLM02 | Sensitive Information Disclosure | **WARN** |
| LLM03 | Supply Chain | **PASS** |
| LLM04 | Data and Model Poisoning | **N/A** |
| LLM05 | Improper Output Handling | **WARN** |
| LLM06 | Excessive Agency | **PASS** |
| LLM07 | System Prompt Leakage | **PASS** |
| LLM08 | Vector and Embedding Weaknesses | **N/A** |
| LLM09 | Misinformation | **WARN** |
| LLM10 | Unbounded Consumption | **WARN** |

**Results:** 3 Pass, 0 Fail, 5 Warn, 2 N/A

---

## Detailed Findings

### LLM01: Prompt Injection — **WARN**

**Findings:**
- User-supplied file content is embedded directly into the audit prompt without sanitization
- Malicious code in audited files could attempt to manipulate audit results
- No input filtering or prompt armoring is applied to collected material

**Remediation:**
- Add content sanitization to collector.py before embedding in prompts
- Implement prompt armoring with clear delimiters between instructions and user content
- Consider a two-pass approach: sanitize first, then audit

---

### LLM02: Sensitive Information Disclosure — **WARN**

**Findings:**
- The collector reads .env.example files and could read files containing secrets
- Collected file content is sent to the Claude API — any secrets in source files will be transmitted
- No redaction of API keys, tokens, or credentials before sending to the API

**Remediation:**
- Add a secrets scanner to collector.py that redacts common patterns (API keys, tokens)
- Exclude .env files and known credential file patterns from collection
- Warn users when potentially sensitive files are detected

---

### LLM03: Supply Chain — **PASS**

**Findings:**
- Minimal dependency footprint — only the anthropic SDK
- Uses pyproject.toml with pinned minimum versions
- No pre-trained models or LoRA adapters in use

---

### LLM04: Data and Model Poisoning — **N/A**

**Findings:**
- This tool does not train or fine-tune models
- OWASP control docs are static local files under version control

---

### LLM05: Improper Output Handling — **WARN**

**Findings:**
- LLM response is parsed as JSON without strict schema validation
- If JSON parsing fails, the error is unhandled and crashes the tool
- Report output is written directly to disk without path validation

**Remediation:**
- Add JSON schema validation for the audit response
- Implement graceful error handling for malformed LLM responses
- Validate and sanitize the output file path

---

### LLM06: Excessive Agency — **PASS**

**Findings:**
- The tool only reads files and writes a single report — minimal agency
- No database connections, network calls (beyond API), or shell execution
- No ability to modify the audited codebase

---

### LLM07: System Prompt Leakage — **PASS**

**Findings:**
- System prompt contains no secrets or credentials
- System prompt is visible in source code (open source) — no security-through-obscurity
- No sensitive operational parameters in the prompt

---

### LLM08: Vector and Embedding Weaknesses — **N/A**

**Findings:**
- No RAG, vector database, or embedding pipeline is used
- OWASP controls are loaded as plain text files, not embeddings

---

### LLM09: Misinformation — **WARN**

**Findings:**
- Audit findings are LLM-generated and could contain false positives or negatives
- No cross-verification or confidence scoring is applied to results
- Users may treat the report as authoritative without independent verification

**Remediation:**
- Add a disclaimer to reports that findings are AI-generated and should be verified
- Consider a multi-pass audit with different prompts to cross-check findings
- Add confidence scores to each control assessment

---

### LLM10: Unbounded Consumption — **WARN**

**Findings:**
- No token budget or cost estimation before making API calls
- Large codebases could generate very large prompts with high token costs
- MAX_TOTAL_SIZE limit exists (500K chars) but no token-based limit

**Remediation:**
- Add token estimation and display expected cost before calling the API
- Add a --max-tokens flag to let users set a budget
- Warn when collected material exceeds a cost threshold

---
