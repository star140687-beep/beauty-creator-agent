import re
from pathlib import Path
from typing import Any, Literal

import yaml  # type: ignore[import-untyped]

from beauty_creator_agent.agents.base import ModelProvider
from beauty_creator_agent.core.errors import ExternalServiceError
from beauty_creator_agent.schemas.compliance import (
    ClaimVerification,
    ComplianceIssue,
    ComplianceResult,
)
from beauty_creator_agent.schemas.content import ContentDraft
from beauty_creator_agent.schemas.evidence import EvidenceItem


class ComplianceSystem:
    """Rule, provenance, and semantic review with fail-closed behavior."""

    def __init__(self, provider: ModelProvider, rules_path: Path | None = None) -> None:
        self.provider = provider
        path = rules_path or Path("config/compliance_rules.yaml")
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        self.rules: list[dict[str, Any]] = payload["rules"]

    def rule_issues(self, draft: ContentDraft) -> list[ComplianceIssue]:
        text = f"{draft.title}\n{draft.body}"
        issues: list[ComplianceIssue] = []
        for rule in self.rules:
            if re.search(str(rule["pattern"]), text, flags=re.IGNORECASE):
                issues.append(
                    ComplianceIssue(
                        code=rule["id"],
                        category=rule["category"],
                        severity=rule["severity"],
                        message=rule["message"],
                    )
                )
        return issues

    def verify_claims(
        self, draft: ContentDraft, evidence: list[EvidenceItem]
    ) -> list[ClaimVerification]:
        known_ids = {item.source_id for item in evidence if item.source_id}
        results: list[ClaimVerification] = []
        for claim in draft.claims:
            required = claim.claim_type in {"product_fact", "consumer_observation"}
            supported = bool(claim.source_ids) and set(claim.source_ids) <= known_ids
            status: Literal["supported", "unsupported", "uncertain"] = (
                "supported" if supported else ("unsupported" if required else "uncertain")
            )
            results.append(
                ClaimVerification(
                    claim_text=claim.text,
                    status=status,
                    source_ids=claim.source_ids,
                    explanation=(
                        "Claim source IDs resolve to evidence"
                        if supported
                        else "Claim lacks resolvable evidence provenance"
                    ),
                )
            )
        return results

    async def check(self, draft: ContentDraft, evidence: list[EvidenceItem]) -> ComplianceResult:
        issues = self.rule_issues(draft)
        verifications = self.verify_claims(draft, evidence)
        for verification in verifications:
            if verification.status == "unsupported":
                issues.append(
                    ComplianceIssue(
                        code="CLAIM_UNSUPPORTED",
                        category="claim_verification",
                        severity="high",
                        message=verification.explanation,
                        claim_text=verification.claim_text,
                    )
                )
        try:
            semantic = await self.provider.check(draft)
            issues.extend(semantic.issues)
        except ExternalServiceError as exc:
            issues.append(
                ComplianceIssue(
                    code="SEMANTIC_REVIEW_ERROR",
                    category="system_error",
                    severity="high",
                    message=str(exc),
                )
            )
        if not issues:
            return ComplianceResult(status="pass", claim_verifications=verifications)
        instructions = list(
            dict.fromkeys([issue.message for issue in issues] + ["仅保留有证据支持的事实表达"])
        )
        return ComplianceResult(
            status="fail",
            issues=issues,
            claim_verifications=verifications,
            revision_instructions=instructions,
        )
