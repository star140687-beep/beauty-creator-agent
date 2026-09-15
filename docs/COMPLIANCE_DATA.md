# Compliance Reference Data and Limits

The compliance module uses linked regulatory references for rule-based screening. Regulatory source metadata is stored in [`regulatory_sources.jsonl`](../data/compliance/regulatory_sources.jsonl), while executable screening rules are defined in [`compliance_rules.yaml`](../config/compliance_rules.yaml).

Each regulatory rule records its target market, source URL, regulatory basis, and effective date where applicable. The current implementation supports `CN`, `US`, and `EU` through `TaskCreate.market`, with `CN` as the default. The same market option is available in the Streamlit interface.

## Official Sources

### CN

* [NMPA efficacy-claim evaluation specification](https://mpa.yn.gov.cn/zfxxgk/zcwj/qtwj/gjwj/202112/t20211222_1224866.html)
* [Cosmetics label rules](https://www.gov.cn/gbgl/bbb734277fe64ea99ef1547669063192/files/05886a5c1b6a4647a159adf25ed38bdd.pdf)

### US

* [FDA cosmetic-label claims guidance](https://www.fda.gov/cosmetics/cosmetics-labeling/cosmetics-labeling-claims)
* [FTC advertising substantiation policy](https://www.ftc.gov/legal-library/browse/ftc-policy-statement-regarding-advertising-substantiation)

### EU

* [Commission Regulation (EU) No 655/2013](https://eur-lex.europa.eu/eli/reg/2013/655/oj/eng)

These references are used as provenance for compliance screening rather than as copies of the underlying regulations. Screening results are treated as review signals: a matched rule can route content for further review, while an unmatched rule does not imply regulatory approval.

Market requirements, product classification, source currency, platform policy, and product-specific evidence still need to be checked before deployment.

## Product-Specific Evidence

The local dataset includes 163 Open Beauty Facts records and 8,494 multi-brand product records collected from crowdsourced or retailer sources.

These records are used for retrieval and product-context testing, but their ingredient lists, descriptions, and consumer reviews are not treated as proof of finished-product efficacy. Product efficacy `claims` remain empty unless supporting evidence is provided through the authorized-product intake flow.

The project does not currently include manufacturer product dossiers, claim-evaluation reports, market authorization or classification records, or approved claim wording for individual SKUs.

The generic product onboarding flow is documented in [`PRODUCTION_DATA.md`](PRODUCTION_DATA.md#onboard-products-from-any-brand). It accepts supporting document URLs for individual claims, but submitted evidence still requires operator or human review before being treated as suitable product evidence.

## Claim Verification

Claim verification checks both the source type and the retrieved evidence text.

A product claim is not accepted when it is supported only by:

* consumer reviews
* an unrelated `source_id`
* evidence text that does not support the claim

Directly matching evidence typed as `official` can be used for product claims when the evidence was added through the documented product-evidence flow. The supplied product name may also be used as a basic name fact.

This check is intentionally conservative. It verifies evidence linkage inside the system but does not determine scientific adequacy or legal approval.

Claims that require product-specific efficacy or safety evidence can therefore be routed to Human Review.

## Claim-Coverage Screening

The compliance service also includes an internal claim-coverage screen for generated title and body content.

It checks fact-like expressions such as:

* `专为…设计`
* `改善`
* `保湿`
* `contains`

When these expressions introduce a product claim that is not covered by directly supported `official` evidence, the content is flagged for revision or Human Review.

This layer complements structured claim verification by checking factual statements that may appear directly in generated prose instead of only in the structured `claims` field.

The claim-coverage screen is heuristic-based and may produce false positives or miss unfamiliar wording. It is used as an additional risk-control layer rather than as a complete factual-claim extractor or automated regulatory decision.

## Compliance Flow

The current compliance path can be summarized as:

```text
Generated Content
      ↓
Rule Engine
      ↓
Claim Verification
      ↓
Claim-Coverage Screening
      ↓
Semantic Review
      ↓
Pass / Revision / Human Review
```

Regulatory rules, evidence verification, and internal screening are kept separate so that the source and purpose of each compliance flag can be inspected during review.
