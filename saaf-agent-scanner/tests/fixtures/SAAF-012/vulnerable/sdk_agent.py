from claude_agent_sdk import ClaudeAgentOptions, query
from langchain_experimental.tools import PythonREPLTool
from mcp.server.fastmcp import FastMCP
import subprocess

mcp = FastMCP("demo")


async def summarize(prompt: str):
    options = ClaudeAgentOptions(
        system_prompt="Summarize the repository",
        allowed_tools=[],
        max_turns=1,
        permission_mode="bypassPermissions",
    )
    async for msg in query(prompt=prompt, options=options):
        yield msg


tools = [PythonREPLTool()]


@mcp.tool()
def run_command(cmd: str) -> str:
    """Run a shell command for the agent."""
    return subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout
