import pytest
from pydantic import ValidationError

from beauty_creator_agent.schemas.task import ProductInput, TaskCreate


def test_task_create_normalizes_whitespace() -> None:
    task = TaskCreate(
        product=ProductInput(name="  Barrier Serum  "),
        platform="xiaohongshu",
        objective="  Generate a launch post  ",
    )

    assert task.product.name == "Barrier Serum"
    assert task.objective == "Generate a launch post"


@pytest.mark.parametrize("platform", ["instagram", "", "XIAOHONGSHU"])
def test_task_create_rejects_invalid_platform(platform: str) -> None:
    with pytest.raises(ValidationError):
        TaskCreate(
            product=ProductInput(name="Barrier Serum"),
            platform=platform,  # type: ignore[arg-type]
            objective="Generate content",
        )


@pytest.mark.parametrize("name", ["", "   "])
def test_product_rejects_empty_name(name: str) -> None:
    with pytest.raises(ValidationError):
        ProductInput(name=name)


def test_task_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        TaskCreate.model_validate(
            {
                "product": {"name": "Barrier Serum"},
                "platform": "xiaohongshu",
                "objective": "Generate content",
                "unexpected": True,
            }
        )
