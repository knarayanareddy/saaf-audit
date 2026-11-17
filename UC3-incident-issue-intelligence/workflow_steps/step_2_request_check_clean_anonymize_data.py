"""
Goal:
- Retrieve the minimum required incident data and make it safe and usable.

Input:
- Structured audit context object
- MCP incident source definition
- Raw incident records

Output:
- Validated and normalized incident dataset
- PII-masked incident dataset
- Data-quality flags for incomplete or malformed records

Code:
- Request only required MCP fields
- Validate required fields are present
- Normalize statuses, timestamps, tags, priorities, and identifiers
- Detect and mask/remove PII such as names and email addresses
- Reject or flag records that are incomplete or malformed

AI:
- Haiku 4.5: detect obvious PII and sensitive free-text content during preprocessing
- Sonnet 4.6: interpret noisy free-text fields where normalization needs semantic assistance
"""

