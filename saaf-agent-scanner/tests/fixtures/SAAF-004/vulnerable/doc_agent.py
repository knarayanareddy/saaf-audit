import anthropic

client = anthropic.Anthropic()


def assess_document(audit_context: str, pbc_description: str, document_text: str) -> str:
    user = (
        f"Audit context : {audit_context}\n\n"
        f"PBC request   : {pbc_description}\n\n"
        f"Extracted document text:\n"
        f"{document_text}\n"
    )
    resp = client.messages.create(model="claude-x", max_tokens=500, system="You are an audit assistant.",
                                  messages=[{"role": "user", "content": user}])
    return resp.content[0].text
