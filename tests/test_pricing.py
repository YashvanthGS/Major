import pytest
from app.pricing import RateCard, compute_payment

RC = RateCard()


def test_hand_computed_example():
    # 10 L, 4.0% fat, 8.5% SNF  ->  10.3 kg
    # fat 0.412 kg * 450 = 185.40 ; snf 0.8755 kg * 200 = 175.10 ; no penalty/bonus
    r = compute_payment(10, 4.0, 8.5, RC)
    assert r["fat_amount"] == 185.40
    assert r["snf_amount"] == 175.10
    assert r["total"] == 360.50


def test_higher_quality_earns_more_for_same_litres():
    low = compute_payment(10, 3.2, 8.2, RC)["total"]
    high = compute_payment(10, 5.0, 9.0, RC)["total"]
    assert high > low


def test_snf_penalty_applies_below_minimum():
    r = compute_payment(10, 4.0, 8.0, RC)  # 0.5 below 8.5
    assert r["snf_penalty"] == round(0.5 * RC.snf_penalty_per_point * 10, 2)


def test_fat_bonus_applies_above_premium():
    r = compute_payment(10, 5.5, 8.6, RC)  # 1.0 over 4.5
    assert r["fat_bonus"] == round(1.0 * RC.fat_bonus_per_point * 10, 2)


def test_no_adjustments_when_disabled():
    rc = RateCard(snf_penalty_per_point=0, fat_bonus_per_point=0)
    r = compute_payment(10, 6.0, 7.0, rc)
    assert r["snf_penalty"] == 0 and r["fat_bonus"] == 0


def test_total_never_negative():
    rc = RateCard(snf_penalty_per_point=1000)
    assert compute_payment(1, 3.0, 6.0, rc)["total"] == 0


def test_quantity_only_baseline_and_gain():
    r = compute_payment(10, 4.0, 8.5, RC)
    assert r["quantity_only_total"] == 320.0
    assert r["quality_gain"] == round(r["total"] - 320.0, 2)


@pytest.mark.parametrize("litres,fat,snf", [(0, 4, 8.5), (-1, 4, 8.5), (10, 0, 8.5), (10, 4, 0), (10, 20, 8.5), (10, 4, 20)])
def test_invalid_inputs_rejected(litres, fat, snf):
    with pytest.raises(ValueError):
        compute_payment(litres, fat, snf, RC)
