from beauty_creator_agent.agents.factory import get_model_provider
from beauty_creator_agent.agents.fake import FakeLLMProvider
from beauty_creator_agent.agents.ollama import OllamaProvider
from beauty_creator_agent.core.config import Settings


def test_factory_builds_default_ollama_provider() -> None:
    provider = get_model_provider(Settings.model_validate({}))

    assert isinstance(provider, OllamaProvider)
    assert provider.planner_model == "llama3.2:3b"
    assert provider.writer_model == "qwen2.5:14b"
    assert provider.compliance_model == "llama3.2:3b"


def test_factory_can_build_fake_provider() -> None:
    provider = get_model_provider(Settings.model_validate({"llm_provider": "fake"}))

    assert isinstance(provider, FakeLLMProvider)
