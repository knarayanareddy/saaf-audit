import anthropic


def run_crosscheck(vendor_text, org_text):
    client = anthropic.Anthropic()
    user_content = (
        "Document 1 (vendor assurance report):\n"
        + vendor_text
        + "\n---\nDocument 2 (organizational control report):\n"
        + org_text
        + "\nExtract all CUECs and match each one."
    )
    return client.messages.create(model="claude-x", max_tokens=100,
                                  messages=[{"role": "user", "content": user_content}])
