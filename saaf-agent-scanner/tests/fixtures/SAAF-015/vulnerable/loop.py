"""synthetic agent loop where escalation is only advisory"""
import anthropic

MAX_RETRIES = 2


def loop(client, tools, state):
    retries = 0
    for block in tools:
        result = dispatch(block, state)
        if result.get("verdict") == "No-Go":
            retries += 1
            if retries > MAX_RETRIES:
                result["escalate_to_human"] = True
        state.append(result)
    return state
