from beauty_creator_agent.agents.factory import get_model_provider
from beauty_creator_agent.agents.fake import FakeLLMProvider
from beauty_creator_agent.agents.ollama import OllamaProvider
from beauty_creator_agent.core.config import Settings


def test_factory_builds_default_ollama_provider() -> None:
    provider = get_model_provider(Settings.model_validate({}))

    assert isinstance(provider, OllamaProvider)
    assert provider.planner_model == "qwen2.5:14b"


def test_factory_can_build_fake_provider() -> None:
    provider = get_model_provider(Settings.model_validate({"llm_provider": "fake"}))

    assert isinstance(provider, FakeLLMProvider)
