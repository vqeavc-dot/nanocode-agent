from __future__ import annotations

from openai import APIConnectionError

from nanocode.llm import OpenAICompatibleLLM


class FakeUsage:
    def model_dump(self):
        return {"prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5, "ignored": "x"}


class FakeMessage:
    def model_dump(self, exclude_none=True):
        return {"role": "assistant", "content": "ok"}


class FakeChoice:
    message = FakeMessage()


class FakeResponse:
    choices = [FakeChoice()]
    usage = FakeUsage()


class FakeCompletions:
    def __init__(self):
        self.calls = 0

    def create(self, **kwargs):
        self.calls += 1
        if self.calls == 1:
            request = type("Request", (), {"method": "POST", "url": "https://example.test"})()
            raise APIConnectionError(request=request)
        return FakeResponse()


class FakeChat:
    def __init__(self):
        self.completions = FakeCompletions()


class FakeClient:
    def __init__(self):
        self.chat = FakeChat()


def test_llm_retries_and_returns_usage():
    llm = OpenAICompatibleLLM("key", "https://example.test", "model", max_retries=1, retry_delay=0)
    llm.client = FakeClient()

    response = llm.chat([], [])

    assert response.message["content"] == "ok"
    assert response.usage == {"prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5}
    assert llm.client.chat.completions.calls == 2
