"""Regression tests for fixes applied during the pre-prod audit.

Each test documents the bug it guards against (file:line at time of fix). Pure
(no-DB) tests live here; DB/auth/HTTP tests live in test_api_security.py.
"""
import re
from decimal import Decimal


# ── Cashback FIXED reward must never exceed the topup ────────────────────────
# Bug: apps/loyalty/models/cashback.py compute_reward() returned the full fixed
# `value` even when it exceeded the amount the client paid in → free money.
def test_cashback_fixed_reward_capped_at_topup():
    from apps.loyalty.models import CashbackRule
    rule = CashbackRule(deposit_threshold=Decimal("30"), accrual_type="fixed", value=Decimal("50"))
    # Pays 40, fixed reward 50 → must be capped to 40, not 50.
    assert rule.compute_reward(Decimal("40")) == Decimal("40")
    # When topup comfortably exceeds the fixed value, the full value is given.
    assert rule.compute_reward(Decimal("100")) == Decimal("50")
    # Below threshold → nothing.
    assert rule.compute_reward(Decimal("10")) == Decimal("0")


def test_cashback_percent_reward_unchanged():
    from apps.loyalty.models import CashbackRule
    rule = CashbackRule(deposit_threshold=Decimal("0"), accrual_type="percent", value=Decimal("5"))
    assert rule.compute_reward(Decimal("200")) == Decimal("10.00")


# ── Category slug must be valid ASCII even for a Cyrillic name ────────────────
# Bug: a Russian category name produced a Cyrillic slug, which Django's SlugField
# rejects → 400/500 on create. The serializer now derives a safe ASCII slug.
def test_category_slug_ascii_from_cyrillic_name():
    from apps.shops.api.v1.serializers.category import CategorySerializer
    slug = CategorySerializer._gen_slug("Напитки")
    assert slug, "slug must be non-empty"
    assert re.fullmatch(r"[a-z0-9-]+", slug), f"slug must be ASCII slug, got {slug!r}"


def test_category_slug_from_latin_name_keeps_base():
    from apps.shops.api.v1.serializers.category import CategorySerializer
    slug = CategorySerializer._gen_slug("Energy Drinks")
    assert slug.startswith("energy-drinks-")
    assert re.fullmatch(r"[a-z0-9-]+", slug)
