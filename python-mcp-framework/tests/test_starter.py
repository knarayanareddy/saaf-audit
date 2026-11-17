import asyncio
import importlib.util
import json
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_real_stdio_initialization_and_empty_tools():
    smoke = load_script("smoke_test")
    assert asyncio.run(smoke.check(sys.executable, ["-m", "usecase_mcp"], True)) == []


def test_config_is_parseable_and_uses_existing_venv():
    for client in ("codex", "claude"):
        output = subprocess.check_output(
            [sys.executable, str(ROOT / "scripts/client_config.py"), client,
             "--name", "invoice-search"], text=True
        )
        if client == "codex":
            config = tomllib.loads(output)["mcp_servers"]["invoice-search"]
        else:
            config = json.loads(output)["mcpServers"]["invoice-search"]
        assert Path(config["command"]).is_file()
        assert ".venv" in Path(config["command"]).parts
        assert config["args"] == ["-m", "usecase_mcp"]
        assert config["env"] == {"MCP_SERVER_NAME": "invoice-search"}


def test_bundle_allowlist_excludes_local_data(tmp_path):
    bundle = load_script("build_bundle")
    package = tmp_path / "src/usecase_mcp"
    package.mkdir(parents=True)
    (package / "server.py").write_text("# server")
    (package / ".env").write_text("SECRET=do-not-ship")
    (tmp_path / ".env").write_text("SECRET=do-not-ship")
    (package / "notes.json").write_text("{}")
    assert bundle.source_files(tmp_path) == [package / "server.py"]


def test_config_requires_valid_use_case_name():
    for extra in ([], ["--name", "bad.name"], ["--name", ""], ["--name", "a\nb"]):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/client_config.py"), "codex", *extra],
            text=True, capture_output=True,
        )
        assert result.returncode == 2
        assert result.stdout == ""


def test_generated_config_reports_use_case_identity():
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    output = subprocess.check_output(
        [sys.executable, str(ROOT / "scripts/client_config.py"), "claude",
         "--name", "invoice-search"], text=True,
    )
    config = json.loads(output)["mcpServers"]["invoice-search"]

    async def connect():
        async with asyncio.timeout(20):
            async with stdio_client(StdioServerParameters(**config)) as (read, write):
                async with ClientSession(read, write) as session:
                    result = await session.initialize()
                    assert result.server_info.name == "invoice-search"
                    assert (await session.list_tools()).tools == []

    asyncio.run(connect())
