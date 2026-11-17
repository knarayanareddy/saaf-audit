"""CO-4: the package stays small and local: standard library only, no network, nothing from input is executed."""
import ast
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1] / "src" / "no_silent_pass"

# Every module the package may import. Adding an import means adding it here on purpose.
ALLOWED = {
    "__future__", "argparse", "dataclasses", "datetime", "decimal", "enum", "json", "math", "os", "re", "sys", "typing",
    "uuid",
}
NETWORK_OR_PROCESS = {"socket", "ssl", "http", "urllib", "requests", "httpx", "ftplib", "smtplib", "subprocess", "asyncio"}
DYNAMIC = {"eval", "exec", "compile", "__import__"}


def sources():
    return sorted(PACKAGE.rglob("*.py"))


def imported_modules(tree):
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name.split(".")[0]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            yield node.module.split(".")[0]


def test_the_package_has_source_files():
    assert len(sources()) >= 8


def test_only_the_standard_library_modules_on_the_allow_list_are_imported():
    for path in sources():
        for module in imported_modules(ast.parse(path.read_text(encoding="utf-8"))):
            assert module in ALLOWED, f"{path.name} imports {module!r}: add it to ALLOWED on purpose, or remove it"


def test_no_network_or_process_modules():
    assert not (ALLOWED & NETWORK_OR_PROCESS)
    for path in sources():
        found = set(imported_modules(ast.parse(path.read_text(encoding="utf-8")))) & NETWORK_OR_PROCESS
        assert not found, f"{path.name} imports {sorted(found)}"


def test_nothing_is_evaluated_or_executed():
    for path in sources():
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id not in DYNAMIC, f"{path.name}:{node.lineno} calls {node.func.id}()"


def test_the_project_declares_no_runtime_dependencies():
    text = (PACKAGE.parents[1] / "pyproject.toml").read_text(encoding="utf-8")
    assert "dependencies = []" in text


def test_the_guard_is_available_as_black_knight_and_under_its_package_name():
    text = (PACKAGE.parents[1] / "pyproject.toml").read_text(encoding="utf-8")
    assert 'black-knight = "no_silent_pass.cli:main"' in text
    assert 'no-silent-pass = "no_silent_pass.cli:main"' in text
    assert (PACKAGE / "__main__.py").exists()
