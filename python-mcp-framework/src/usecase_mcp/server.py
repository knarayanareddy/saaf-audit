"""Empty, runnable stdio server. Add tools only after completing intake."""

import logging
import sys

from mcp.server import MCPServer

from usecase_mcp.config import Settings
from usecase_mcp.tools import register_tools


def create_server() -> MCPServer:
    settings = Settings.from_environment()
    server = MCPServer(settings.name)
    register_tools(server)
    return server


def main() -> None:
    logging.basicConfig(level=logging.WARNING, stream=sys.stderr)
    create_server().run(transport="stdio")


if __name__ == "__main__":
    main()
