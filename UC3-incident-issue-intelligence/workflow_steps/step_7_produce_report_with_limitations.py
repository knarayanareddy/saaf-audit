"""
Goal:
- Generate a usable Incident Intelligence Report without leaking sensitive data.

Input:
- Prioritized clusters and high-risk issues
- Materiality assessments
- Trend, root-cause, and classification outputs
- Data-quality and confidence notes

Output:
- Incident Intelligence Report in JSON/Markdown
- Hotspots and audit attention flags
- Limitations, confidence notes, and PII-safe final output

Code:
- Build the final JSON/Markdown output
- Include metrics, hotspots, classifications, flags, and limitations
- Run a final PII/output safety check
- Attach confidence notes and data-quality warnings

AI:
- Haiku 4.5: draft simple narrative summaries of hotspots and recurring issues
- Sonnet 4.6: explain limitations and uncertainty in reviewer-friendly language
- Sonnet 4.6: assist with concise narrative sections for the final report
"""
