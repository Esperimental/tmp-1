from __future__ import annotations

from pathlib import Path


TEXT_SUFFIXES = {".md", ".json", ".py", ".toml", ".txt", ".yaml", ".yml"}
SENSITIVE_NAME_PARTS = {"credential", "password", "secret", "token"}


def visible_text_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if any(part.startswith(".") for part in relative.parts):
            continue
        if path.suffix not in TEXT_SUFFIXES:
            continue
        name_parts = set(path.stem.lower().replace("-", "_").split("_"))
        if name_parts & SENSITIVE_NAME_PARTS:
            continue
        files.append(path)
    return files


def workspace_summary(root: Path, content_limit: int = 12_000) -> str:
    files = visible_text_files(root)
    sections = ["Files:", *[str(path.relative_to(root)) for path in files[:200]]]
    remaining = content_limit
    omitted = 0
    for path in files:
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if remaining <= 0:
            omitted += 1
            continue
        excerpt = content[:remaining]
        sections.extend([f"\n--- {path.relative_to(root)} ---", excerpt])
        remaining -= len(excerpt)
        if len(excerpt) < len(content):
            omitted += 1
    if omitted:
        sections.append(f"\n[{omitted} file contents omitted due to context budget]")
    return "\n".join(sections)


def workspace_snapshot(root: Path, content_limit: int = 16_000) -> dict[str, object]:
    included: dict[str, str] = {}
    omitted: list[str] = []
    remaining = content_limit
    for path in visible_text_files(root):
        relative = str(path.relative_to(root))
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if len(content) > remaining:
            omitted.append(relative)
            continue
        included[relative] = content
        remaining -= len(content)
    return {"included": included, "omitted": omitted, "content_limit": content_limit}
