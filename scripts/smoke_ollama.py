import asyncio

from beauty_creator_agent.agents.ollama import OllamaProvider
from beauty_creator_agent.schemas.task import ProductInput, TaskCreate


async def main() -> None:
    provider = OllamaProvider(timeout_seconds=180)
    request = TaskCreate(
        product=ProductInput(
            brand="澄光实验室",
            name="屏障修护精华",
            description="含神经酰胺、角鲨烷和泛醇。",
        ),
        platform="xiaohongshu",
        objective="生成自然、不夸张的新品介绍",
        audience="干性及敏感肌用户",
    )
    decision = await provider.plan(request)
    print(decision.model_dump_json(indent=2))


if __name__ == "__main__":
    asyncio.run(main())
