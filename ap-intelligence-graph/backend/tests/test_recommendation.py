"""Tests for Step 2: hardened recommendation output.

Covers the specific gap found in the pre-launch audit - a syntactically
valid but structurally wrong LLM response (missing key, wrong type,
malformed recommended_terms) would previously reach chat.py/recommendations.py's
direct dict-key access and crash as an unhandled 500 *after* the model call
had already "succeeded." These tests prove that path now falls back to the
deterministic provider instead, exactly like a call failure does.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import app.llm.factory as factory
import pytest
from pydantic import ValidationError

from app.agents.recommendation_agent import generate_recommendation
from app.llm.provider import LLMProvider
from app.llm.recommendation_schema import RawRecommendationOut, validate_raw_recommendation

VALID_CONTEXT = {"client_name": "Northwind Outfitters", "partner_name": "Summit Sisters"}
VALID_RAW = {
    "recommendation": "renegotiate_and_test",
    "recommended_terms": {"base_fee": 3500, "performance_bonus_pct": 10, "bonus_basis": "verified_new_customer_revenue"},
    "confidence": 0.74,
    "uncertainties": ["Promo-code leakage is suspected but not verified."],
    "explanation": "Because reasons.",
}


# ---- schema unit tests ----

def test_valid_shape_passes():
    result = validate_raw_recommendation(VALID_RAW)
    assert result["recommendation"] == "renegotiate_and_test"
    assert result["recommended_terms"]["base_fee"] == 3500.0
    assert "supporting_memory_ids" not in result  # never part of the LLM-facing schema


def test_missing_confidence_field_rejected():
    bad = {k: v for k, v in VALID_RAW.items() if k != "confidence"}
    with pytest.raises(ValidationError):
        validate_raw_recommendation(bad)


def test_confidence_wrong_type_rejected():
    bad = {**VALID_RAW, "confidence": "very high"}
    with pytest.raises(ValidationError):
        validate_raw_recommendation(bad)


def test_confidence_out_of_range_rejected():
    bad = {**VALID_RAW, "confidence": 1.5}
    with pytest.raises(ValidationError):
        validate_raw_recommendation(bad)


def test_recommended_terms_missing_bonus_basis_rejected():
    bad = {**VALID_RAW, "recommended_terms": {"base_fee": 3500, "performance_bonus_pct": 10}}
    with pytest.raises(ValidationError):
        validate_raw_recommendation(bad)


def test_recommended_terms_not_a_dict_rejected():
    bad = {**VALID_RAW, "recommended_terms": "3500 base plus 10% bonus"}
    with pytest.raises(ValidationError):
        validate_raw_recommendation(bad)


def test_base_fee_non_positive_rejected():
    bad = {**VALID_RAW, "recommended_terms": {**VALID_RAW["recommended_terms"], "base_fee": -100}}
    with pytest.raises(ValidationError):
        validate_raw_recommendation(bad)


def test_blank_recommendation_rejected():
    bad = {**VALID_RAW, "recommendation": "   "}
    with pytest.raises(ValidationError):
        validate_raw_recommendation(bad)


def test_entirely_non_dict_result_rejected():
    with pytest.raises((ValidationError, TypeError)):
        validate_raw_recommendation(["not", "a", "dict"])


# ---- fallback-path integration tests ----

class _BrokenProviderBase(LLMProvider):
    name = "broken_test_provider"

    def extract_claims(self, *a, **k):
        raise NotImplementedError

    def summarize(self, *a, **k):
        raise NotImplementedError


class _MissingFieldProvider(_BrokenProviderBase):
    def recommend(self, question, evidence_brief, context):
        return {
            "recommendation": "renew",
            "recommended_terms": {"base_fee": 3500, "performance_bonus_pct": 10, "bonus_basis": "x"},
        }  # missing "confidence"


class _WrongTypeProvider(_BrokenProviderBase):
    def recommend(self, question, evidence_brief, context):
        return {**VALID_RAW, "confidence": "high"}


class _BadTermsProvider(_BrokenProviderBase):
    def recommend(self, question, evidence_brief, context):
        return {**VALID_RAW, "recommended_terms": {"base_fee": 3500}}  # missing bonus fields


class _NotADictProvider(_BrokenProviderBase):
    def recommend(self, question, evidence_brief, context):
        return ["totally", "malformed"]


class _RaisesProvider(_BrokenProviderBase):
    def recommend(self, question, evidence_brief, context):
        raise ValueError("simulated malformed JSON from the API call itself")


@pytest.mark.parametrize(
    "broken_provider_cls",
    [_MissingFieldProvider, _WrongTypeProvider, _BadTermsProvider, _NotADictProvider, _RaisesProvider],
)
def test_call_with_fallback_recovers_from_every_failure_mode(monkeypatch, broken_provider_cls):
    monkeypatch.setattr(factory, "get_provider", lambda: broken_provider_cls())
    result, provider_name = factory.call_with_fallback(
        "recommend", "question", "evidence brief", VALID_CONTEXT, validate=validate_raw_recommendation
    )
    assert provider_name == "mock_deterministic (fallback)"
    # the result itself must still be a fully valid, safe structured recommendation
    RawRecommendationOut(**result)


@pytest.mark.parametrize(
    "broken_provider_cls",
    [_MissingFieldProvider, _WrongTypeProvider, _BadTermsProvider, _NotADictProvider, _RaisesProvider],
)
def test_generate_recommendation_never_raises_on_malformed_model_output(monkeypatch, broken_provider_cls):
    """This is the exact function chat.py and recommendations.py call - it
    must never let a malformed model response propagate as an exception."""
    monkeypatch.setattr(factory, "get_provider", lambda: broken_provider_cls())
    result, provider_name = generate_recommendation(
        "Summit Sisters wants $6,000 for another campaign. Should we renew them?",
        "TRUSTED CLIENT MEMORY\n- ...",
        VALID_CONTEXT,
    )
    assert provider_name.endswith("(fallback)")
    assert isinstance(result["recommendation"], str) and result["recommendation"]
    assert 0.0 <= result["confidence"] <= 1.0
    assert set(result["recommended_terms"]) == {"base_fee", "performance_bonus_pct", "bonus_basis"}
    assert "supporting_memory_ids" not in result


def test_healthy_live_provider_is_not_overridden_by_validation(monkeypatch):
    """Sanity check the happy path: a well-formed live response passes
    through validate() unchanged and is NOT routed to the fallback."""

    class _HealthyProvider(_BrokenProviderBase):
        name = "healthy_test_provider"

        def recommend(self, question, evidence_brief, context):
            return dict(VALID_RAW)

    monkeypatch.setattr(factory, "get_provider", lambda: _HealthyProvider())
    result, provider_name = generate_recommendation("q", "brief", VALID_CONTEXT)
    assert provider_name == "healthy_test_provider"
    assert result["recommendation"] == "renegotiate_and_test"
