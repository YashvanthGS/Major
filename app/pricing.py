"""
Quality-based milk pricing (FAT/SNF).

Payment = value of the fat content + value of the SNF content (+/- quality adjustments),
so two farmers who deliver the same litres get different amounts if their milk quality differs.

    weight_kg = litres * density            (milk density ~1.03 kg/L)
    fat_kg    = weight_kg * FAT% / 100
    snf_kg    = weight_kg * SNF% / 100
    base      = fat_kg * fat_rate + snf_kg * snf_rate

Adjustments (all optional, set to 0 to disable):
    * SNF penalty : below `min_snf`, deduct `snf_penalty_per_point` per litre per 1.0 SNF point short.
    * Fat bonus   : above `premium_fat`, add `fat_bonus_per_point` per litre per 1.0 FAT point over.
"""
from dataclasses import dataclass, asdict


@dataclass
class RateCard:
    fat_rate: float = 450.0              # Rs per kg of fat
    snf_rate: float = 200.0              # Rs per kg of SNF
    density: float = 1.03                # kg per litre
    min_snf: float = 8.5                 # standard SNF %
    snf_penalty_per_point: float = 1.5   # Rs per litre per SNF point below min_snf
    premium_fat: float = 4.5             # FAT % above which a bonus applies
    fat_bonus_per_point: float = 1.0     # Rs per litre per FAT point above premium_fat
    flat_rate_per_litre: float = 32.0    # quantity-only baseline, used for comparison

    def to_dict(self):
        return asdict(self)


def validate_reading(litres: float, fat: float, snf: float) -> None:
    if litres <= 0:
        raise ValueError("litres must be greater than 0")
    if not 0 < fat <= 15:
        raise ValueError("FAT % must be between 0 and 15")
    if not 0 < snf <= 15:
        raise ValueError("SNF % must be between 0 and 15")


def compute_payment(litres: float, fat: float, snf: float, rc: RateCard) -> dict:
    validate_reading(litres, fat, snf)

    weight_kg = litres * rc.density
    fat_kg = weight_kg * fat / 100
    snf_kg = weight_kg * snf / 100

    fat_amount = fat_kg * rc.fat_rate
    snf_amount = snf_kg * rc.snf_rate

    snf_short = max(0.0, rc.min_snf - snf)
    snf_penalty = snf_short * rc.snf_penalty_per_point * litres

    fat_over = max(0.0, fat - rc.premium_fat)
    fat_bonus = fat_over * rc.fat_bonus_per_point * litres

    total = max(0.0, fat_amount + snf_amount - snf_penalty + fat_bonus)
    quantity_only = litres * rc.flat_rate_per_litre

    return {
        "litres": round(litres, 2),
        "fat": fat,
        "snf": snf,
        "weight_kg": round(weight_kg, 3),
        "fat_kg": round(fat_kg, 4),
        "snf_kg": round(snf_kg, 4),
        "fat_amount": round(fat_amount, 2),
        "snf_amount": round(snf_amount, 2),
        "snf_penalty": round(snf_penalty, 2),
        "fat_bonus": round(fat_bonus, 2),
        "total": round(total, 2),
        "rate_per_litre": round(total / litres, 2),
        "quantity_only_total": round(quantity_only, 2),
        "quality_gain": round(total - quantity_only, 2),
    }
