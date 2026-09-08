from beauty_creator_agent.agents.base import ModelProvider
from beauty_creator_agent.agents.fake import FakeLLMProvider
from beauty_creator_agent.agents.ollama import OllamaProvider
from beauty_creator_agent.core.config import Settings, get_settings


def get_model_provider(settings: Settings | None = None) -> ModelProvider:
    """Build the configured model provider."""
    resolved = settings or get_settings()
    if resolved.llm_provider == "fake":
        return FakeLLMProvider()
    return OllamaProvider(
        base_url=resolved.llm_base_url,
        planner_model=resolved.planner_model,
        writer_model=resolved.writer_model,
        compliance_model=resolved.compliance_model,
    )
