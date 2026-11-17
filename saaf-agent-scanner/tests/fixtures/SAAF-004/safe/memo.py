from llm import complete

PROMPT = "Draft a memo for vendor {vendor_name} in sector {sector}."


def draft(profile):
    prompt = PROMPT.format(vendor_name=profile.name, sector=profile.sector)
    return complete(model="x", user=prompt)
