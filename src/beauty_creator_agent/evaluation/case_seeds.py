"""Hand-selected gold anchors for a reproducible 80-case component benchmark.

Twenty real, crowdsourced product identities are crossed with four evaluation
dimensions. Gold labels are authored here, not inferred from system outputs.
"""

from typing import Any

# (OBF source_id, brand, product name, retrieval query)
PRODUCTS = [
    (
        "openbeautyfacts:0019100109940",
        "Jergens",
        "Jergens Original Scent Dry Skin Moisturizer",
        "Jergens Original Scent Dry Skin Moisturizer",
    ),
    (
        "openbeautyfacts:0020714689186",
        "Clinique",
        "Clinique for Men Oil-Control Mattifying Moisturizer",
        "Clinique for Men Oil-Control",
    ),
    (
        "openbeautyfacts:0052800482685",
        "Lubriderm",
        "Lubriderm Intense Skin Repair",
        "Lubriderm Intense Skin Repair",
    ),
    (
        "openbeautyfacts:0062600061065",
        "Aveeno",
        "daily moisturizer with salicylic acid",
        "Aveeno daily moisturizer salicylic acid",
    ),
    (
        "openbeautyfacts:0062600061515",
        "Aveeno",
        "ultra-calming sensitive skin foaming cleanser",
        "ultra-calming sensitive skin foaming cleanser",
    ),
    (
        "openbeautyfacts:0062600380579",
        "Neutrogena",
        "Ultra Sheeran Body Mist Sunscreen",
        "Ultra Sheeran Body Mist Sunscreen",
    ),
    (
        "openbeautyfacts:0070501060902",
        "Neutrogena",
        "Deep Clean Facial Cleanser",
        "Neutrogena Deep Clean Facial Cleanser",
    ),
    (
        "openbeautyfacts:0070501113424",
        "Neutrogena",
        "Hydro Boost Water Gel Lotion SPF 50",
        "Hydro Boost Water Gel Lotion SPF 50",
    ),
    (
        "openbeautyfacts:0075486091125",
        "Hawaiian Tropic",
        "Sunscreen Clear Spray Weightless Hydration SPF 30",
        "Hawaiian Tropic Weightless Hydration SPF 30",
    ),
    (
        "openbeautyfacts:0075609011016",
        "Olay",
        "Olay Complete Daily Moisturizer with Sunscreen SPF 30",
        "Olay Complete Daily Moisturizer with Sunscreen SPF 30",
    ),
    (
        "openbeautyfacts:0079656044966",
        "Banana Boat",
        "UltraSport Faces Sunscreen Lotion UVA/UVB Broad Spectrum SPF 30",
        "Banana Boat UltraSport Faces Sunscreen",
    ),
    (
        "openbeautyfacts:0085275710434",
        "CeraVe",
        "CeraVe Foaming Facial Cleanser",
        "CeraVe Foaming Facial Cleanser",
    ),
    (
        "openbeautyfacts:0086800870258",
        "Neutrogena",
        "sport face oil-free lotion sunscreen 70",
        "Neutrogena sport face oil-free sunscreen 70",
    ),
    (
        "openbeautyfacts:0302994113002",
        "Cetaphil",
        "Cetaphil Oil-Free Facial Moisturizer with Sunscreen SPF 35",
        "Cetaphil Oil-Free Facial Moisturizer SPF 35",
    ),
    (
        "openbeautyfacts:0303162046450",
        "Blue Lizard",
        "Sensitive Mineral Sunscreen",
        "Blue Lizard Sensitive Mineral Sunscreen",
    ),
    (
        "openbeautyfacts:0607845023180",
        "NARS",
        "Pure Radiant Tinted Moisturizer SPF 30",
        "NARS Pure Radiant Tinted Moisturizer SPF 30",
    ),
    (
        "openbeautyfacts:0655439060004",
        "Paula's Choice",
        "Paula's Choice CLEAR Pore Normalizing Cleanser",
        "Paula's Choice CLEAR Pore Normalizing Cleanser",
    ),
    (
        "openbeautyfacts:0676280014510",
        "Hempz",
        "Vanilla Plum Herbal Body Moisturizer",
        "Hempz Vanilla Plum Herbal Body Moisturizer",
    ),
    (
        "openbeautyfacts:0682223020135",
        "Jack Black",
        "Jack Black Pure Clean Daily Facial Cleanser",
        "Jack Black Pure Clean Daily Facial Cleanser",
    ),
    (
        "openbeautyfacts:0871760000445",
        "Sun Bum",
        "Premium Moisturizing Sunscreen Lotion SPF 30",
        "Sun Bum Premium Moisturizing Sunscreen Lotion SPF 30",
    ),
]


# Gold labels are risk flags requiring review, not final legal judgments.
RISK_SCENARIOS = [
    ("CN", "100%有效", True),
    ("CN", "治疗痤疮", True),
    ("CN", "国家药监局认证", True),
    ("CN", "药妆级修护", True),
    ("CN", "零风险使用", True),
    ("CN", "临床证实7天祛斑", True),
    ("CN", "抗皱功效已证实", True),
    ("US", "Treats eczema", True),
    ("US", "Regrows hair", True),
    ("US", "Restores collagen production", True),
    ("EU", "EU approved", True),
    ("EU", "European Commission approved", True),
    ("CN", "轻薄质地，日常好搭配", False),
    ("CN", "柔和的使用感受因人而异", False),
    ("CN", "日常清洁步骤分享", False),
    ("US", "A light texture for daily use", False),
    ("US", "Soft finish; individual experiences vary", False),
    ("EU", "A simple daily cleansing routine", False),
    ("EU", "A lightweight texture", False),
    ("CN", "产品名称与包装信息请以实物为准", False),
]


def build_cases() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for index, (source_id, brand, name, query) in enumerate(PRODUCTS, 1):
        market = "CN"
        if (index - 1) % 5 == 0:
            intent = "compliance_only"
            objective = f"仅审核现有的{name}文案，不要改写"
        elif index % 2 == 0:
            intent = "rewrite"
            objective = f"改写{name}的已有文案"
        else:
            intent = "generate"
            objective = f"生成{name}的新品介绍"
        request: dict[str, Any] = {
            "product": {"brand": brand, "name": name},
            "platform": "xiaohongshu",
            "market": market,
            "objective": objective,
        }
        if intent != "generate":
            request["existing_content"] = f"关于{name}的旧文案。"
        cases.append(
            {
                "id": f"route_{index:02}",
                "kind": "routing",
                "request": request,
                "expected_intent": intent,
            }
        )
        cases.append(
            {
                "id": f"rag_{index:02}",
                "kind": "retrieval",
                "query": query,
                "expected_source_id": source_id,
            }
        )
        supported = index % 2 == 0
        claim_text = f"产品名称为{name}" if supported else "该产品能治疗痤疮"
        ground_request = {
            "product": {"brand": brand, "name": name},
            "platform": "xiaohongshu",
            "market": market,
            "objective": f"生成{name}的保守产品介绍，仅陈述可核实的事实",
        }
        evidence = {
            "id": "user_product_name" if supported else f"obf_{index}",
            "evidence_type": "product_fact",
            "source_type": "user_input" if supported else "external_search",
            "source_id": "user_product_input" if supported else source_id,
            "content": f"产品名称：{name}" if supported else f"Third-party listing for {name}.",
            "reliability": "high" if supported else "medium",
        }
        cases.append(
            {
                "id": f"ground_{index:02}",
                "kind": "grounding",
                "request": ground_request,
                "claim_text": claim_text,
                "evidence": evidence,
                "expected_supported": supported,
            }
        )
        risk_market, phrase, expected_risk = RISK_SCENARIOS[index - 1]
        cases.append(
            {
                "id": f"risk_{index:02}",
                "kind": "compliance",
                "market": risk_market,
                "title": phrase,
                "body": "美妆内容审核样本。",
                "expected_risk": expected_risk,
            }
        )
    return cases
