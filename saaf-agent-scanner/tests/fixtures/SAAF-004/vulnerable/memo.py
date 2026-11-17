from llm import complete

PROMPT = "Review this evidence and give a conclusion:\n{evidence_text}\nAnswer with JSON."


def draft(evidence_text):
    prompt = PROMPT.format(evidence_text=evidence_text)
    return complete(model="x", user=prompt)
