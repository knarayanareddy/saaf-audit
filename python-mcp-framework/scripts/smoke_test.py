"""Exercise real MCP initialization and tools/list without calling any tools."""

import argparse
import asyncio
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def check(command: str, args: list[str], expect_empty: bool = False) -> list[str]:
    async with asyncio.timeout(20):
        async with stdio_client(StdioServerParameters(command=command, args=args)) as (read, write):
            async with ClientSession(read, write) as session:
                result = await session.initialize()
                tools = await session.list_tools()
                names = [tool.name for tool in tools.tools]
                if expect_empty and names:
                    raise AssertionError(f"Expected no starter tools, received {names}")
                print(f"Connected to {result.server_info.name}; tools: {names}")
                return names


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expect-empty", action="store_true")
    parser.add_argument("--bundle", help="Path to an extracted bundle's server.py")
    args = parser.parse_args()
    command_args = [args.bundle] if args.bundle else ["-m", "usecase_mcp"]
    asyncio.run(check(sys.executable, command_args, args.expect_empty))


if __name__ == "__main__":
    main()
