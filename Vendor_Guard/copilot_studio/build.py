"""Build the Copilot Studio package from the repo's single source of truth.

Framework knowledge is copied from prompts/ so the Python agents and the
Copilot Studio agent never drift apart.

Usage: python copilot_studio/build.py [--out copilot_studio/dist]
"""
import argparse
import shutil
from pathlib import Path

HERE = Path(__file__).parent
PROMPTS_DIR = HERE.parent / "prompts"

# prompts/ files that are Python-pipeline internals, not framework knowledge
EXCLUDED_PROMPTS = {"document_validity.md"}

# Knowledge files that live in copilot_studio/ because only the Copilot agent uses them
COPILOT_ONLY_KNOWLEDGE = ["document_validity_rules.md", "subcontracting_chain.md"]

# Copilot Studio limit for agent instructions (characters)
INSTRUCTIONS_MAX_CHARS = 8000


def build(out_dir: Path) -> list[Path]:
    instructions = (HERE / "agent_instructions.md").read_text(encoding="utf-8")
    if len(instructions) > INSTRUCTIONS_MAX_CHARS:
        raise ValueError(
            f"agent_instructions.md is {len(instructions)} chars; "
            f"Copilot Studio allows {INSTRUCTIONS_MAX_CHARS}."
        )

    knowledge_dir = out_dir / "knowledge"
    # Only clean what this script generates; never delete the whole out_dir,
    # which may be a directory the user pointed --out at.
    if knowledge_dir.exists():
        shutil.rmtree(knowledge_dir)
    knowledge_dir.mkdir(parents=True)

    written = [out_dir / "agent_instructions.md"]
    (out_dir / "agent_instructions.md").write_text(instructions, encoding="utf-8")

    for src in sorted(PROMPTS_DIR.glob("*.md")):
        if src.name in EXCLUDED_PROMPTS:
            continue
        dest = knowledge_dir / src.name
        shutil.copyfile(src, dest)
        written.append(dest)

    # Copilot-only knowledge files (not used by the Python pipeline)
    for name in COPILOT_ONLY_KNOWLEDGE:
        dest = knowledge_dir / name
        shutil.copyfile(HERE / name, dest)
        written.append(dest)
    return written


def main():
    parser = argparse.ArgumentParser(description="Build the Copilot Studio package")
    parser.add_argument("--out", type=Path, default=HERE / "dist")
    args = parser.parse_args()
    for path in build(args.out):
        print(path)


if __name__ == "__main__":
    main()
