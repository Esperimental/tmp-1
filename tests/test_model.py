from types import SimpleNamespace

import pytest

from evolver.model import ModelResponseError, OpenAIModel


class FakeClient:
    def __init__(self, responses: list[str]) -> None:
        self.responses = list(responses)
        self.inputs: list[str] = []
        self.responses_api = self

    @property
    def responses(self):
        return self.responses_api

    @responses.setter
    def responses(self, value):
        self._responses = value

    def create(self, **kwargs):
        self.inputs.append(kwargs["input"])
        return SimpleNamespace(output_text=self._responses.pop(0))


def test_model_retries_one_malformed_json_response() -> None:
    client = FakeClient(["not json", '{"argv":["printf","ok"]}'])

    argv = OpenAIModel(client=client).propose_command(
        SimpleNamespace(to_dict=lambda: {"id": "x"}), "state"
    )

    assert argv == ["printf", "ok"]
    assert len(client.inputs) == 2
    assert "previous response was invalid" in client.inputs[1]


def test_model_stops_after_one_malformed_json_retry() -> None:
    client = FakeClient(["not json", "still not json"])

    with pytest.raises(ModelResponseError):
        OpenAIModel(client=client).propose_command(
            SimpleNamespace(to_dict=lambda: {"id": "x"}), "state"
        )

    assert len(client.inputs) == 2
