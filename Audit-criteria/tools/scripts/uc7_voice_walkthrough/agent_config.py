"""ElevenLabs agent definition for the audit walkthrough interviewer.

Run this module to print the JSON you paste into the ElevenLabs dashboard (or
push with the ElevenLabs CLI) when creating the agent:

    python -m tools.scripts.uc7_voice_walkthrough.agent_config

The two client tools declared here must be registered by name on the client
side (see ``rcm_tools.RcmSession`` and ``walkthrough.py``).
"""

import json

AGENT_SYSTEM_PROMPT = """\
You are an internal audit assistant conducting a process walkthrough by voice.
You are interviewing the owner of the process to build a Risk and Control Matrix
(RCM). Speak in short, natural spoken turns — one question at a time.

Walk through the process sub-process by sub-process. For each step:
1. Ask how the step works and what its objective is.
2. Ask what could go wrong (the risk).
3. Ask what prevents or detects that (the control): who performs it, is it manual
   or automated, and how often.

When you have a clear risk and its control, call the `capture_control` tool with
the sub-process, the risk, the control, and whether the control is Manual or
Automated. If a step has no control, still call `capture_control` with an empty
control_description so the gap is recorded.

Do not invent risks the owner did not confirm; capture only what they tell you.
When the owner says the walkthrough is complete, confirm how many items you
captured, then call `build_rcm`. Read back the summary it returns — the risk
count and any sub-process without a control — and ask the owner to confirm or
correct it. Then thank them and end.
"""

FIRST_MESSAGE = (
    "Hi, I'm your audit assistant. I'll walk through the process with you to build "
    "the risk and control matrix. Which process are we covering, and what's the "
    "first step?"
)

# Client-tool declarations for the ElevenLabs agent config.
CLIENT_TOOLS = [
    {
        "type": "client",
        "name": "capture_control",
        "description": (
            "Record one risk and its mitigating control as elicited during the "
            "walkthrough. Call once per risk. Leave control_description empty if the "
            "step has no control."
        ),
        "expects_response": True,
        "parameters": {
            "type": "object",
            "properties": {
                "sub_process": {"type": "string", "description": "The sub-process/step being discussed."},
                "business_objective": {"type": "string", "description": "What the step is meant to achieve."},
                "risk_description": {"type": "string", "description": "What could go wrong."},
                "control_description": {"type": "string", "description": "The mitigating control, or empty if none."},
                "control_type": {"type": "string", "enum": ["Manual", "Automated"], "description": "Manual or Automated."},
                "control_frequency": {"type": "string", "description": "How often the control runs, e.g. 'every transaction'."},
                "impact": {"type": "string", "enum": ["High", "Medium", "Low"], "description": "Risk impact."},
                "likelihood": {"type": "string", "enum": ["High", "Medium", "Low"], "description": "Risk likelihood."},
            },
            "required": ["sub_process", "risk_description"],
        },
    },
    {
        "type": "client",
        "name": "build_rcm",
        "description": (
            "Build the Risk and Control Matrix from everything captured so far. Call "
            "once, when the walkthrough is complete. Returns a spoken summary to read back."
        ),
        "expects_response": True,
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
]


def agent_definition() -> dict:
    """Return the full agent config as a dict."""
    return {
        "name": "Audit Walkthrough Interviewer (UC7)",
        "conversation_config": {
            "agent": {
                "prompt": {"prompt": AGENT_SYSTEM_PROMPT, "tools": CLIENT_TOOLS},
                "first_message": FIRST_MESSAGE,
                "language": "en",
            }
        },
    }


if __name__ == "__main__":
    print(json.dumps(agent_definition(), indent=2))
