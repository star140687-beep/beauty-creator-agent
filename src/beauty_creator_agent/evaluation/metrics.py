from dataclasses import dataclass


@dataclass(slots=True)
class Metric:
    name: str
    passed: int = 0
    total: int = 0

    @property
    def score(self) -> float:
        return self.passed / self.total if self.total else 0.0

    def record(self, passed: bool) -> None:
        self.total += 1
        self.passed += int(passed)

    def as_dict(self) -> dict[str, str | int | float]:
        return {"name": self.name, "passed": self.passed, "total": self.total, "score": self.score}
