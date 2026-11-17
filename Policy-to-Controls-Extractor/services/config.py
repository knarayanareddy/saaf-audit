import configparser
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ============================================================================
# 1. Configuratie
# ============================================================================
# Laadt standaardwaarden en overschrijft die met lokale instellingen uit P2C.conf.

def load_config(config_file: Path) -> configparser.ConfigParser:
    config = configparser.ConfigParser()
    config["paths"] = {"todo_dir": "testdata/to-do", "output_dir": "testdata/output"}
    config["defaults"] = {"domain": "unknown", "scope": "unknown"}
    config["anthropic"] = {"api_key": ""}
    # model       -> control-extractie (zwaar); header_model -> headingdetectie (licht)
    config["claude"] = {
        "model": "claude-opus-4-6",
        "header_model": "claude-haiku-4-5-20251001",
    }
    if config_file.exists():
        config.read(config_file)
    return config


def get_runtime_settings(
    config: configparser.ConfigParser,
) -> Tuple[Path, Path, Optional[Path], str, str, str, str, str]:
    todo_dir = Path(config["paths"]["todo_dir"])
    output_dir = Path(config["paths"]["output_dir"])
    halfway_dir = Path(config["paths"]["halfway_dir"]) if "halfway_dir" in config["paths"] else None
    domain = config["defaults"]["domain"]
    scope = config["defaults"]["scope"]
    model = config["claude"]["model"]
    header_model = config["claude"]["header_model"]
    api_key = config["anthropic"]["api_key"]
    return todo_dir, output_dir, halfway_dir, domain, scope, model, header_model, api_key


def resolve_input_files(todo_dir: Path, requested_file: Optional[Path]) -> Dict[str, List[Path]]:
    if requested_file is not None:
        if not requested_file.exists():
            raise FileNotFoundError(f"Bestand niet gevonden: {requested_file}")
        suffix = requested_file.suffix.lower()
        if suffix == ".pdf":
            return {"pdf_files": [requested_file], "doc_files": []}
        if suffix in (".docx", ".doc"):
            return {"pdf_files": [], "doc_files": [requested_file]}
        raise ValueError(f"Niet-ondersteund bestandstype: {requested_file.suffix}. Gebruik PDF of DOCX.")

    pdf_files = sorted(list(todo_dir.glob("*.pdf")))
    doc_files = sorted(list(todo_dir.glob("*.docx")) + list(todo_dir.glob("*.doc")))

    if not pdf_files and not doc_files:
        raise FileNotFoundError(f"Geen PDF- of DOCX-bestanden gevonden in {todo_dir}/")

    return {
        "pdf_files": pdf_files,
        "doc_files": doc_files,
    }
