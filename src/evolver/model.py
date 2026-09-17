from __future__ import annotations

import json
import os
from typing import Any, Protocol

from openai import OpenAI

from .domain import Plan, Step


class AgentModel(Protocol):
    def create_plan(self, objective: str, repository_summary: str) -> Plan: ...

    def propose_command(self, step: Step, repository_summary: str) -> list[str]: ...


class ModelResponseError(ValueError):
    """The model did not return the required structured response after retry."""


def _json_object(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        cleaned = "\n".join(lines[1:-1])
    value = json.loads(cleaned)
    if not isinstance(value, dict):
        raise ValueError("Model response must be a JSON object")
    return value


class OpenAIModel:
    def __init__(self, model: str | None = None, client: Any | None = None) -> None:
        self._client = client or OpenAI()
        self._model = model or os.environ.get("EVOLVER_MODEL", "gpt-5.6-luna")

    @property
    def model_name(self) -> str:
        return self._model

    def _ask(self, instructions: str, prompt: str) -> dict:
        retry_prompt = prompt
        for attempt in range(2):
            response = self._client.responses.create(
                model=self._model,
                instructions=instructions,
                input=retry_prompt,
            )
            try:
                return _json_object(response.output_text)
            except (ValueError, json.JSONDecodeError) as error:
                if attempt:
                    raise ModelResponseError(
                        f"Invalid structured model response after one retry: {error}"
                    ) from error
                retry_prompt = (
                    f"{prompt}\n\nYour previous response was invalid structured JSON: {error}. "
                    "Return exactly one JSON object matching the requested schema, with no prose or code fence."
                )
        raise AssertionError("unreachable")

    def create_plan(self, objective: str, repository_summary: str) -> Plan:
        value = self._ask(
            "You are a conservative planner. Return JSON only. Make the fewest bounded "
            "steps possible. Allowed verification kinds are stdout_equals, stdout_equals_file, "
            "file_content_equals and exit_code_equals. Use stdout_equals_file with path when output must match "
            "an existing file. Schema: {objective:string,steps:[{id:string,"
            "instruction:string,verification:{kind:string,expected:string,path?:string}}]}.",
            f"Objective:\n{objective}\n\nCurrent repository state:\n{repository_summary}",
        )
        value["objective"] = objective
        return Plan.from_dict(value)

    def propose_command(self, step: Step, repository_summary: str) -> list[str]:
        value = self._ask(
            "Return JSON only with schema {argv:[string,...]}. Propose one direct process "
            "invocation. Shell syntax, redirection, pipes and command chaining are unavailable. "
            "Do not use a shell wrapper such as sh -c or bash -c.",
            f"Step:\n{json.dumps(step.to_dict())}\n\nRepository state and prior evidence:\n{repository_summary}",
        )
        argv = value.get("argv")
        if not isinstance(argv, list) or not argv or not all(isinstance(x, str) for x in argv):
            raise ValueError("Model must return a non-empty argv string array")
        if argv[0] in {"sh", "bash", "zsh", "fish"}:
            raise ValueError("Shell wrappers are not allowed")
        return argv
