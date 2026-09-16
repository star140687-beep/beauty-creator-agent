import re
from pathlib import Path
from typing import Literal

import yaml  # type: ignore[import-untyped]

from beauty_creator_agent.agents.base import ModelProvider
from beauty_creator_agent.core.errors import ExternalServiceError
from beauty_creator_agent.schemas.common import Market
from beauty_creator_agent.schemas.compliance import (
    ClaimVerification,
    ComplianceIssue,
    ComplianceResult,
    ComplianceRule,
)
from beauty_creator_agent.schemas.content import ContentDraft, GeneratedClaim
from beauty_creator_agent.schemas.evidence import EvidenceItem

PROSE_FACT_CUES = re.compile(
    r"专为.{0,24}(?:设计|打造)|改善|缓解|修护|滋润|锁水|锁住水分|补水|保湿|"
    r"适合.{0,16}(?:肤质|肌肤)|含有|成分|防晒|抗皱|祛斑|"
    r"\b(?:designed for|improv\w*|moisturiz\w*|hydrat\w*|contains?|helps?)\b",
    flags=re.IGNORECASE,
)


class ComplianceSystem:
    """Rule, provenance, and semantic review with fail-closed behavior."""

    def __init__(self, provider: ModelProvider, rules_path: Path | None = None) -> None:
        self.provider = provider
        path = rules_path or Path("config/compliance_rules.yaml")
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        self.rules = [ComplianceRule.model_validate(row) for row in payload["rules"]]
        for rule in self.rules:
            re.compile(rule.pattern)

    def rule_issues(self, draft: ContentDraft, market: Market = "CN") -> list[ComplianceIssue]:
        text = f"{draft.title}\n{draft.body}"
        issues: list[ComplianceIssue] = []
        for rule in self.rules:
            if market in rule.markets and re.search(rule.pattern, text, flags=re.IGNORECASE):
                issues.append(
                    ComplianceIssue(
                        code=rule.id,
                        category=rule.category,
                        severity=rule.severity,
                        message=rule.message,
                        market=market,
                        source_url=rule.source_url,
                        source_basis=rule.basis,
                        regulatory_source_id=rule.regulatory_source_id,
                    )
                )
        return issues

    def verify_claims(
        self, draft: ContentDraft, evidence: list[EvidenceItem]
    ) -> list[ClaimVerification]:
        known = {item.source_id: item for item in evidence if item.source_id}
        results: list[ClaimVerification] = []
        for claim in draft.claims:
            required = claim.claim_type in {"product_fact", "consumer_observation"}
            matched = [known.get(source_id) for source_id in claim.source_ids]
            supported = bool(matched) and all(
                item is not None and self._evidence_supports(claim, item) for item in matched
            )
            status: Literal["supported", "unsupported", "uncertain"] = (
                "supported" if supported else ("unsupported" if required else "uncertain")
            )
            results.append(
                ClaimVerification(
                    claim_text=claim.text,
                    status=status,
                    source_ids=claim.source_ids,
                    explanation=(
                        "Claim is directly supported by relevant evidence text and provenance"
                        if supported
                        else "Claim lacks relevant, directly matching evidence provenance"
                    ),
                )
            )
        return results

    def prose_claim_issues(
        self,
        draft: ContentDraft,
        evidence: list[EvidenceItem],
        verifications: list[ClaimVerification] | None = None,
    ) -> list[ComplianceIssue]:
        """Fail closed on fact-like prose omitted from supported structured claims.

        This internal cue screen is deliberately conservative and is not a
        complete NLP claim extractor or a legal classification.
        """
        text = f"{draft.title}\n{draft.body}"
        for item in evidence:
            if item.id == "user_product_name":
                name = item.content.split("：", 1)[-1].strip()
                text = text.replace(name, "")
        checks = verifications if verifications is not None else self.verify_claims(draft, evidence)
        known = {item.source_id: item for item in evidence if item.source_id}
        supported_prose_claims = [
            claim.text.casefold()
            for claim, check in zip(draft.claims, checks, strict=True)
            if check.status == "supported"
            and claim.claim_type == "product_fact"
            and claim.source_ids
            and all(
                known.get(source_id) is not None
                and (
                    known[source_id].source_type == "official"
                    or known[source_id].id == "user_product_description"
                    or known[source_id].metadata.get("upload_role") == "product_material"
                )
                for source_id in claim.source_ids
            )
        ]
        for match in PROSE_FACT_CUES.finditer(text):
            before = re.split(r"[。！？!?；;，,\n.]", text[: match.start()])[-1]
            after = re.split(r"[。！？!?；;，,\n.]", text[match.end() :])[0]
            clause = f"{before}{match.group(0)}{after}".strip().casefold()
            if any(claim in clause or clause in claim for claim in supported_prose_claims):
                continue
            return [
                ComplianceIssue(
                    code="PROSE_FACT_UNVERIFIED",
                    category="claim_coverage",
                    severity="high",
                    message="Fact-like prose lacks directly matching allowed product evidence",
                    claim_text=match.group(0),
                    source_basis="Internal conservative claim-coverage policy",
                    regulatory_source_id="internal-claim-coverage-policy",
                )
            ]
        return []

    @staticmethod
    def _evidence_supports(claim: GeneratedClaim, item: EvidenceItem) -> bool:
        text = claim.text.casefold().strip()
        content = item.content.casefold()
        if claim.claim_type == "product_fact":
            if item.evidence_type != "product_fact":
                return False
            if item.source_type == "official":
                return text in content
            if item.source_type == "user_input" and (
                item.id == "user_product_description"
                or item.metadata.get("upload_role") == "product_material"
            ):
                return text in content
            if item.source_type == "user_input" and item.id == "user_product_name":
                name = content.split("：", 1)[-1].strip()
                return text in {name, f"产品名称为{name}", f"product name is {name}"}
            return False
        if claim.claim_type == "consumer_observation":
            return item.evidence_type in {"consumer_review", "consumer_insight"} and text in content
        return text in content

    async def check(
        self, draft: ContentDraft, evidence: list[EvidenceItem], *, market: Market = "CN"
    ) -> ComplianceResult:
        issues = self.rule_issues(draft, market)
        verifications = self.verify_claims(draft, evidence)
        issues.extend(self.prose_claim_issues(draft, evidence, verifications))
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
