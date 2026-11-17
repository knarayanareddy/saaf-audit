"""synthetic agent loop where escalation stops the run"""
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
                return {"requires_human_review": True, "state": state}
        state.append(result)
    return state
