from pathlib import Path

from evolver.workspace import workspace_snapshot, workspace_summary


def test_workspace_context_is_bounded_and_excludes_sensitive_named_files(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text("x" * 20, encoding="utf-8")
    (tmp_path / "secret_notes.txt").write_text("do-not-share", encoding="utf-8")
    (tmp_path / "large.txt").write_text("y" * 100, encoding="utf-8")

    summary = workspace_summary(tmp_path, content_limit=30)
    snapshot = workspace_snapshot(tmp_path, content_limit=30)

    assert "do-not-share" not in summary
    assert "secret_notes.txt" not in summary
    assert "visible content" not in summary
    assert "app.py" in snapshot["included"]
    assert "large.txt" in snapshot["omitted"]
