import re
import anthropic


def rate(client, report_text):
    msg = client.messages.create(model="claude-x", max_tokens=200,
                                 messages=[{"role": "user", "content": report_text}])
    answer = msg.content[0].text
    m = re.search(r"overall rating:\s*(\w+)", answer, re.I)
    rating = m.group(1)
    return {"rating": rating}
