from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Verification:
    kind: str
    expected: str
    path: str | None = None

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Verification":
        kind = str(value["kind"])
        if kind not in {"stdout_equals", "file_content_equals"}:
            raise ValueError(f"Unsupported verification kind: {kind}")
        path = value.get("path")
        if kind == "file_content_equals" and not path:
            raise ValueError("file_content_equals requires path")
        return cls(kind=kind, expected=str(value["expected"]), path=path)

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"kind": self.kind, "expected": self.expected}
        if self.path is not None:
            result["path"] = self.path
        return result


@dataclass(frozen=True)
class Step:
    id: str
    instruction: str
    verification: Verification

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Step":
        return cls(
            id=str(value["id"]),
            instruction=str(value["instruction"]),
            verification=Verification.from_dict(value["verification"]),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "instruction": self.instruction,
            "verification": self.verification.to_dict(),
        }


@dataclass(frozen=True)
class Plan:
    objective: str
    steps: tuple[Step, ...]

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Plan":
        steps = tuple(Step.from_dict(item) for item in value["steps"])
        if not steps:
            raise ValueError("Plan must contain at least one step")
        if len({step.id for step in steps}) != len(steps):
            raise ValueError("Step ids must be unique")
        return cls(objective=str(value["objective"]), steps=steps)

    def to_dict(self) -> dict[str, Any]:
        return {"objective": self.objective, "steps": [s.to_dict() for s in self.steps]}
