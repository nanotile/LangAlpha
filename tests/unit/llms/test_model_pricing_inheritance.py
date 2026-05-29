"""Tests for ModelConfig.get_model_pricing() parent-provider inheritance."""

import pytest

from src.llms.llm import ModelConfig


class TestGetModelPricing:
    """OAuth/variant models carry no pricing of their own and inherit the
    parent provider's entry for the same model_id."""

    @pytest.fixture
    def model_config(self):
        return ModelConfig()

    def test_direct_provider_pricing(self, model_config):
        pricing = model_config.get_model_pricing("claude-opus-4-8")
        assert pricing is not None
        assert pricing["input"] == 5.0
        assert pricing["output"] == 25.0

    def test_oauth_variant_inherits_parent_pricing(self, model_config):
        """claude-oauth has no pricing list; falls back to anthropic."""
        pricing = model_config.get_model_pricing("claude-opus-4-8-oauth")
        assert pricing is not None
        assert pricing["input"] == 5.0
        assert pricing["output"] == 25.0

    def test_oauth_1m_variant_inherits_parent_pricing(self, model_config):
        pricing = model_config.get_model_pricing("claude-opus-4-8-oauth-1m")
        assert pricing is not None
        assert pricing["input"] == 5.0

    def test_intl_variant_uses_own_pricing_not_parent(self, model_config):
        """dashscope-intl has its own pricing list, so it must NOT inherit the
        cheaper CN rates from the parent dashscope provider."""
        cn = model_config.get_model_pricing("qwen3.7-max")
        intl = model_config.get_model_pricing("qwen3.7-max-intl")
        assert cn["input"] == 1.714
        assert intl["input"] == 2.677
        assert cn["input"] != intl["input"]

    def test_unknown_model_returns_none(self, model_config):
        assert model_config.get_model_pricing("does-not-exist") is None
