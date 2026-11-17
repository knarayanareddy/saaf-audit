"""
Customs rules.

Each rule has an identifier, a severity, a short title, a plain English reason
shown to the contributor, and one or more patterns. Patterns are regular
expressions matched without regard to case.

To add a phrase: add a pattern to the right rule, then add a test case in
tests/test_customs.py. Keep reasons readable for someone who is not a developer.

Rules with negation_guard=True are skipped when the same clause forbids the
behaviour ("Never send...", "Do not finalise ... without approval"), so that
guardrail wording in a legitimate skill is not reported as an attack.

Patterns with a group named "dest" capture a destination. If that destination
is on the approved domain list, the match is not reported.
"""

import re

SEVERITIES = ["Informational", "Low", "Medium", "High", "Critical"]


def _c(*patterns):
    return [re.compile(p, re.IGNORECASE) for p in patterns]


# Characters that are invisible or reorder text. They can hide an instruction
# from a human reviewer while an AI agent still reads it. Unicode tag
# characters (U+E0000 to U+E007F) are handled separately in customs.py, which
# also decodes the hidden text they carry.
HIDDEN_CHARACTERS = {
    "\u200b": "zero width space",
    "\u200c": "zero width non-joiner",
    "\u200d": "zero width joiner",
    "\u200e": "left-to-right mark",
    "\u200f": "right-to-left mark",
    "\u202a": "left-to-right embedding",
    "\u202b": "right-to-left embedding",
    "\u202c": "pop directional formatting",
    "\u202d": "left-to-right override",
    "\u202e": "right-to-left override",
    "\u2060": "word joiner",
    "\u2061": "invisible function application",
    "\u2062": "invisible times",
    "\u2063": "invisible separator",
    "\u2064": "invisible plus",
    "\u2066": "left-to-right isolate",
    "\u2067": "right-to-left isolate",
    "\u2068": "first strong isolate",
    "\u2069": "pop directional isolate",
    "\ufeff": "byte order mark",
}

# Words that forbid an action. Used by negation_guard.
NEGATION = re.compile(
    r"\b(do not|don't|dont|never|must not|mustn't|should not|shouldn't|"
    r"cannot|can't|may not|niet|nooit|geen)\b",
    re.IGNORECASE,
)
# Phrases that look negative but are not ("Don't forget to upload...").
NOT_A_NEGATION = re.compile(
    r"\b(do not|don't|dont|never)\s+forget\b|\bvergeet\s+(dit\s+)?niet\b",
    re.IGNORECASE,
)

_DEST = r"(?P<dest>https?://|ftp://|s3://|[\w.+-]+@[\w-]+\.[a-z]{2,})"

LINE_RULES = [
    dict(
        id="CUS-O1",
        severity="High",
        title="Instruction override",
        negation_guard=True,
        reason=(
            "Tells the agent to set aside its instructions, act without approval "
            "or keep something from the person using it. A shared skill should "
            "never do this."
        ),
        patterns=_c(
            r"\b(ignore|disregard|forget|override)\s+(all\s+|any\s+|the\s+|your\s+)?"
            r"(previous|prior|earlier|above|preceding|original|system|other)\s+"
            r"(instructions?|rules|guidance|prompts?|messages?|guardrails?)\b",
            r"\b(skip|bypass|disable|turn\s+off|switch\s+off|circumvent|ignore)\s+"
            r"(the\s+|all\s+|any\s+|your\s+)?(human\s+)?(approval|review|confirmation|"
            r"sign[\s-]?off|guardrail|safety\s+check|check|logging|audit\s+trail)s?\b",
            r"\b(proceed|continue|act|run|execute|approve|send|delete|submit|merge|"
            r"finali[sz]e|complete)\w*\b[^.\n]{0,40}\bwithout\s+(asking|confirmation|"
            r"approval|review|telling|informing|notifying|checking)\b",
            r"\b(do\s+not|don't|never)\s+(tell|inform|notify|alert|warn)\s+the\s+"
            r"(user|auditor|reviewer|human|operator)\b",
            r"\b(hide|conceal|keep)\s+(this|it|these\s+\w+|the\s+\w+)\s+(secret\s+)?"
            r"from\s+the\s+(user|auditor|reviewer|human|operator)\b",
            r"\byou\s+are\s+now\s+(in\s+)?(developer|admin|administrator|unrestricted|"
            r"jailbreak|god)\s*mode\b",
            r"\b(new|updated|real|override)\s+system\s+(prompt|instructions?)\b",
            # Dutch
            r"\b(negeer|vergeet)\s+(alle\s+|de\s+)?(vorige|eerdere|bovenstaande|"
            r"oorspronkelijke)\s+(instructies|regels|opdrachten|prompts?)\b",
            r"\b(sla|slaat)\b[^.\n]{0,30}\b(goedkeuring|review|controle|bevestiging|"
            r"beoordeling)\b[^.\n]{0,10}\bover\b",
            r"\bzonder\s+(te\s+)?(vragen|toestemming|goedkeuring|overleg|bevestiging|"
            r"melden)\b",
            r"\b(vertel|meld|zeg)\b[^.\n]{0,20}\bniet\s+(aan|tegen)\s+de\s+"
            r"(gebruiker|auditor|reviewer)\b",
            r"\bschakel\s+(de\s+)?(beveiliging|controles?|logging|goedkeuring|"
            r"guardrails?)\s+uit\b",
        ),
    ),
    dict(
        id="CUS-N1",
        severity="High",
        title="Sends data out",
        negation_guard=True,
        reason=(
            "Instructs the agent to send or copy data to an outside destination. "
            "In an audit setting this is a direct route for leaking workpapers or "
            "client data."
        ),
        patterns=_c(
            r"\b(upload|send|post|forward|transmit|exfiltrate|copy|e-?mail|sync|share|"
            r"submit|push)\w*\b[^\n]{0,80}?\b(to|into)\b[^\n]{0,40}?" + _DEST,
            r"\b(upload|stuur|verstuur|verzend|mail|kopieer|deel)\w*\b[^\n]{0,80}?"
            r"\bnaar\b[^\n]{0,40}?" + _DEST,
            r"\brequests\.(post|put|patch)\s*\(",
            r"\bcurl\b[^\n]*\s(-d|--data[\w-]*|-F|--form|-T|--upload-file)\s",
            r"\bInvoke-(WebRequest|RestMethod)\b[^\n]*-Method\s+(Post|Put)\b",
        ),
    ),
    dict(
        id="CUS-N4",
        severity="Medium",
        title="Network command",
        reason=(
            "Runs a network command. A shared skill should rarely need to fetch or "
            "send data on its own. Check where it connects and why."
        ),
        patterns=_c(
            r"\b(curl|wget|scp|rsync|netcat|ncat|sftp|Invoke-WebRequest|"
            r"Invoke-RestMethod)\s+\S",
            r"\bfetch\s*\(\s*['\"`]https?://",
            r"\brequests\.get\s*\(",
            r"\burllib\.request\b",
            r"\bgit\s+clone\s+\S",
            r"\bhttpx\.\w+\s*\(",
        ),
    ),
    dict(
        id="CUS-N5",
        severity="High",
        title="Downloads and runs code",
        reason=(
            "Downloads code and runs it immediately, so whatever the server returns "
            "on the day is executed with the agent's permissions."
        ),
        patterns=_c(
            r"\b(curl|wget|iwr|irm|Invoke-WebRequest|Invoke-RestMethod)\b[^\n|]*\|\s*"
            r"(sudo\s+)?((ba|z|k)?sh|iex|Invoke-Expression|python3?|node|perl|ruby)\b",
            r"\b(ba)?sh\s+<\(\s*(curl|wget)\b",
            r"\b(iex|Invoke-Expression)\s*\(\s*(New-Object|iwr|irm|Invoke-WebRequest)",
        ),
    ),
    dict(
        id="CUS-S1",
        severity="High",
        title="Reaches outside its scope",
        reason=(
            "Refers to credential files, keys or locations outside the project "
            "folder. An audit skill has no reason to read these."
        ),
        patterns=_c(
            r"~/\.ssh\b",
            r"\bid_(rsa|dsa|ecdsa|ed25519)\b",
            r"\.aws/(credentials|config)\b",
            r"\.git-credentials\b",
            r"(?<![\w-])\.(netrc|npmrc|pypirc)\b",
            r"\.kube/config\b",
            r"/etc/(passwd|shadow|sudoers)\b",
            r"%APPDATA%|AppData[\\/]+Roaming",
            r"\b(login\s+)?keychain\b",
            r"\b(browser|chrome|edge|firefox)\s+(cookies|passwords|saved\s+logins)\b",
            r"\b(read|open|cat|load|print|include|copy|upload|send|show|dump|lees)\b"
            r"[^\n]{0,40}(?<![\w-])\.env\b(?![\w-])",
        ),
    ),
    dict(
        id="CUS-P1",
        severity="High",
        title="Removes approval or permission limits",
        reason=(
            "Gives the agent blanket permissions or switches off approval prompts, "
            "so actions would run without a person seeing them first."
        ),
        patterns=_c(
            r"\b(auto_?approve|always_?allow|allow_?all|trust_?all|bypass_?permissions|"
            r"skip_?permissions|no_?confirm|yolo)\b",
            r"\bdangerously[\w-]*",
            r"\bBash\(\s*\*?\s*\)",
            r"[\"'](allow|allowed|allowedTools|allowed_tools|permissions|tools)[\"']\s*:"
            r"\s*\[\s*[\"']\*[\"']",
            r"\b(permission_?mode)[\"']?\s*[:=]\s*[\"']?(bypass|allow_?all)",
        ),
    ),
    dict(
        id="CUS-P2",
        severity="Medium",
        title="Adds or downloads agent tools",
        reason=(
            "Adds a tool server or downloads a package when the agent starts. Check "
            "where it comes from and pin an exact version rather than the latest one."
        ),
        patterns=_c(
            r"[\"']?(mcpServers|mcp_servers|mcp\.servers|context_servers)[\"']?\s*[:=]",
            r"\bnpx\s+(-y|--yes)\b",
            r"\buvx\s+\S",
            r"@latest\b",
            r"\bdocker\s+run\b[^\n]*:latest\b",
        ),
    ),
    dict(
        id="CUS-H4",
        severity="Medium",
        title="Hidden styling",
        reason=(
            "Uses styling that hides text from a human reader. Anything hidden this "
            "way is still read by an agent."
        ),
        patterns=_c(
            r"display\s*:\s*none",
            r"visibility\s*:\s*hidden",
            r"font-size\s*:\s*0(px|pt|em|rem)?\s*[;\"']",
            r"(?<![\w-])color\s*:\s*(white|#fff\b|#ffffff|transparent)",
            r"opacity\s*:\s*0(\.0+)?\s*[;\"']",
        ),
    ),
]

URL = re.compile(r"\b(?:https?|ftp|s3)://(?P<host>[^/\s)\"'<>\]`,]+)", re.IGNORECASE)
EMAIL = re.compile(
    r"(?<![\w.+-])[\w.+-]+@(?P<domain>[a-z0-9-]+(?:\.[a-z0-9-]+)*\.[a-z]{2,})\b",
    re.IGNORECASE,
)
ENCODED = re.compile(r"(?<![A-Za-z0-9+/=])[A-Za-z0-9+/]{60,}={0,2}(?![A-Za-z0-9+/=])")
HTML_COMMENT = re.compile(r"<!--(.*?)(?:-->|\Z)", re.DOTALL)
