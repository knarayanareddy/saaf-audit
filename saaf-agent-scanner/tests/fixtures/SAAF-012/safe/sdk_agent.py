import shlex
import subprocess

from claude_agent_sdk import ClaudeAgentOptions, query
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("demo")
ALLOWED_COMMANDS = {"git-status": ["git", "status", "--short"], "git-diff": ["git", "diff", "--stat"]}


async def summarize(prompt: str):
    options = ClaudeAgentOptions(
        system_prompt="Summarize the repository",
        allowed_tools=["Read", "Grep", "Glob"],
        disallowed_tools=["Bash", "Write", "Edit", "WebFetch"],
        max_turns=1,
        permission_mode="default",
    )
    async for msg in query(prompt=prompt, options=options):
        yield msg


@mcp.tool()
def run_command(name: str) -> str:
    """Run one of the pre-approved commands."""
    if name not in ALLOWED_COMMANDS:
        raise ValueError("command not allowed")
    return subprocess.run(ALLOWED_COMMANDS[name], capture_output=True, text=True).stdout
