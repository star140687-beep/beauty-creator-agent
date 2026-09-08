import pytest
from pydantic import ValidationError

from beauty_creator_agent.core.config import Settings


def test_settings_have_safe_development_defaults() -> None:
    settings = Settings.model_validate({})

    assert settings.app_env == "development"
    assert settings.max_revision_count == 2
    assert settings.llm_api_key is None


def test_settings_reject_invalid_revision_count() -> None:
    with pytest.raises(ValidationError):
        Settings.model_validate({"max_revision_count": -1})
