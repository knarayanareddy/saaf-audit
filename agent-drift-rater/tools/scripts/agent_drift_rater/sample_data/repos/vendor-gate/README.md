# Vendor Gate

Assists an auditor in approving vendor payments. Hard limits are enforced in code, every
decision is logged with its prompt version, and a human approves anything the guard flags.

Hard rules:
- Payments above EUR 1000 must be approved by a human.
- A payment must never exceed the purchase-order amount.
