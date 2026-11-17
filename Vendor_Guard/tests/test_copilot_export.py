import pytest

from copilot_studio import build as copilot_build


def test_build_creates_package(tmp_path):
    written = copilot_build.build(tmp_path / "dist")
    names = {p.name for p in written}
    assert "agent_instructions.md" in names
    assert "document_validity_rules.md" in names
    assert "subcontracting_chain.md" in names
    for fw in ("iso27001_controls.md", "nis2_measures.md", "cbw_requirements.md",
               "dora_requirements.md", "bio2_controls.md", "ai_act_requirements.md",
               "altai_requirements.md", "ec_ethics_guidelines.md"):
        assert fw in names


def test_pipeline_only_prompt_not_exported(tmp_path):
    written = copilot_build.build(tmp_path / "dist")
    assert "document_validity.md" not in {p.name for p in written}


def test_knowledge_matches_prompts_source(tmp_path):
    out = tmp_path / "dist"
    copilot_build.build(out)
    src = copilot_build.PROMPTS_DIR / "dora_requirements.md"
    assert (out / "knowledge" / "dora_requirements.md").read_text() == src.read_text()


def test_instructions_within_copilot_limit():
    text = (copilot_build.HERE / "agent_instructions.md").read_text(encoding="utf-8")
    assert len(text) <= copilot_build.INSTRUCTIONS_MAX_CHARS


def test_instructions_reference_every_knowledge_file(tmp_path):
    out = tmp_path / "dist"
    copilot_build.build(out)
    text = (out / "agent_instructions.md").read_text(encoding="utf-8")
    for f in (out / "knowledge").iterdir():
        assert f.stem in text, f"{f.name} not referenced in agent instructions"


def test_build_rejects_oversized_instructions(tmp_path, monkeypatch):
    monkeypatch.setattr(copilot_build, "INSTRUCTIONS_MAX_CHARS", 10)
    with pytest.raises(ValueError):
        copilot_build.build(tmp_path / "dist")


def test_build_does_not_delete_unrelated_files_in_out_dir(tmp_path):
    keep = tmp_path / "important.txt"
    keep.write_text("keep me")
    copilot_build.build(tmp_path)
    assert keep.read_text() == "keep me"


def test_rebuild_removes_stale_knowledge_files(tmp_path):
    copilot_build.build(tmp_path)
    stale = tmp_path / "knowledge" / "old_framework.md"
    stale.write_text("stale")
    copilot_build.build(tmp_path)
    assert not stale.exists()


def test_instructions_cover_engagement_roles():
    text = (copilot_build.HERE / "agent_instructions.md").read_text(encoding="utf-8")
    for needle in ("Subcontractor", "Vendor of the client", "Client (self-assessment)",
                   "DRAFT for auditor review", "Subcontracting Chain"):
        assert needle in text
