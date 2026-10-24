from documentary.vision import EvidenceVerifier, MatchContract


def test_match_contract_marks_explicit_factual_fields_as_required():
    contract = MatchContract.from_beat({
        "beat_id": "B001",
        "narration_text": "SK hynix is building its Yongin semiconductor cluster in 2026.",
        "verification_level": "FACTUAL_EXACT",
        "verification_requirements": {
            "entity": "SK hynix",
            "location": "Yongin",
            "object": "semiconductor cluster",
            "action": "construction",
            "time": "2026",
        },
        "forbidden_substitutions": ["Samsung factory"],
    })

    assert contract.level == "FACTUAL_EXACT"
    assert contract.required_fields == {
        "entity": "SK hynix",
        "location": "Yongin",
        "object": "semiconductor cluster",
        "action": "construction",
        "time": "2026",
    }
    assert contract.forbidden_substitutions == ["Samsung factory"]


def test_match_contract_uses_existing_visual_description_when_manifest_has_no_explicit_requirements():
    contract = MatchContract.from_beat({
        "beat_id": "B001",
        "source_priority": "must_real",
        "visual_type": "sourced_video",
        "visual_description": "Busan port containers and export loading footage.",
    })

    assert contract.level == "FACTUAL_EXACT"
    assert contract.required_fields["visual_context"] == "Busan port containers and export loading footage."


def test_evidence_verifier_never_auto_accepts_required_unknown_field():
    contract = MatchContract(
        level="FACTUAL_EXACT",
        required_fields={"entity": "SK hynix", "location": "Yongin"},
    )
    result = EvidenceVerifier().decide(contract, {
        "semantic_score": 0.96,
        "fields": {
            "entity": {"status": "CONFIRMED", "evidence": "logo and caption"},
            "location": {"status": "UNKNOWN", "evidence": "location not visible"},
        },
    })

    assert result["decision"] == "REVIEW"
    assert result["auto_accept"] is False
    assert "location" in result["unconfirmed_required_fields"]


def test_evidence_verifier_rejects_contradicted_required_field():
    contract = MatchContract(
        level="FACTUAL_EXACT",
        required_fields={"entity": "SK hynix"},
    )
    result = EvidenceVerifier().decide(contract, {
        "semantic_score": 0.99,
        "fields": {
            "entity": {"status": "CONTRADICTED", "evidence": "Samsung signage is visible"},
        },
    })

    assert result["decision"] == "REJECT"
    assert result["auto_accept"] is False

