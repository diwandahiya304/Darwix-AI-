"""Lead qualification: score_lead(...) -> hot/warm/cold + reasons.

Rules are loaded from voice_agent/config/qualification_rules.yaml, never
hardcoded here and never put in the voice agent's system prompt —
qualification logic must be auditable/tunable independently of the
prompt (CLAUDE.md §1 / the assignment brief's explicit instruction that
this logic lives in code, not the system prompt).

Design: age-out-of-range, budget-too-low, and negative intent are hard
disqualifiers (force COLD regardless of other points) rather than just
heavy point penalties — a real underwriter wouldn't call an under-18
applicant "warm" just because their stated budget is generous. Red-flag
medical conditions are a point penalty, not a hard disqualifier, since
they're still insurable subject to underwriting (per the KB's own
eligibility rules), just less likely to close quickly.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from voice_agent.app.models import LeadTemperature, ScoreLeadArgs, ScoreLeadResult

_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "qualification_rules.yaml"

_rules_cache: dict | None = None


def load_rules() -> dict:
    global _rules_cache
    if _rules_cache is None:
        with _CONFIG_PATH.open(encoding="utf-8") as f:
            _rules_cache = yaml.safe_load(f)
    return _rules_cache


def _score_age(age: int | None, rules: dict, reasons: list[str]) -> tuple[int, bool]:
    points, age_rules = rules["points"], rules["age"]
    if age is None:
        reasons.append("Age not provided — no age-based scoring applied.")
        return 0, False
    if age < age_rules["min_insurable"] or age > age_rules["max_standard"]:
        reasons.append(
            f"Age {age} is outside the standard insurable range "
            f"({age_rules['min_insurable']}-{age_rules['max_standard']})."
        )
        return points["age_out_of_range"], True
    if age <= age_rules["ideal_max"]:
        reasons.append(f"Age {age} is within the ideal range (<= {age_rules['ideal_max']}).")
        return points["age_ideal"], False
    reasons.append(
        f"Age {age} is in the senior underwriting range "
        f"({age_rules['ideal_max']}-{age_rules['max_standard']})."
    )
    return points["age_senior"], False


def _score_budget(budget: int | None, rules: dict, reasons: list[str]) -> tuple[int, bool]:
    points, budget_rules = rules["points"], rules["budget"]
    if budget is None:
        reasons.append("Budget not provided — no budget-based scoring applied.")
        return 0, False
    if budget < budget_rules["min_viable"]:
        reasons.append(
            f"Budget {budget} is below the minimum viable premium "
            f"({budget_rules['min_viable']})."
        )
        return points["budget_too_low"], True
    if budget >= budget_rules["comfortable"]:
        reasons.append(f"Budget {budget} comfortably covers standard plans (>= {budget_rules['comfortable']}).")
        return points["budget_comfortable"], False
    reasons.append(f"Budget {budget} is viable but below the comfortable tier.")
    return points["budget_viable"], False


def _score_family_size(family_size: int | None, rules: dict, reasons: list[str]) -> tuple[int, bool]:
    points = rules["points"]
    threshold = rules["family_size"]["cross_sell_threshold"]
    if family_size is None:
        reasons.append("Family size not provided — no cross-sell scoring applied.")
        return 0, False
    if family_size >= threshold:
        reasons.append(f"Family size {family_size} meets the cross-sell threshold (>= {threshold}).")
        return points["family_cross_sell"], False
    reasons.append(f"Family size {family_size} is below the cross-sell threshold ({threshold}).")
    return 0, False


def _score_conditions(conditions: str | None, rules: dict, reasons: list[str]) -> tuple[int, bool]:
    points, condition_rules = rules["points"], rules["conditions"]
    if not conditions:
        reasons.append("No pre-existing conditions disclosed.")
        return points["condition_neutral_or_none"], False
    lowered = conditions.lower()
    for red_flag in condition_rules["red_flags"]:
        if red_flag in lowered:
            reasons.append(
                f"Disclosed condition matches a red-flag condition ({red_flag}) "
                f"requiring medical underwriting — still insurable, not disqualifying."
            )
            return points["condition_red_flag"], False
    for neutral in condition_rules["neutral"]:
        if neutral in lowered:
            reasons.append(f"Disclosed condition ({neutral}) is coverable per standard waiting-period rules.")
            return points["condition_neutral_or_none"], False
    reasons.append(
        "Disclosed condition noted; not on the red-flag or known-neutral list — "
        "treat as neutral pending underwriting review."
    )
    return points["condition_neutral_or_none"], False


def _score_intent(intent: str | None, rules: dict, reasons: list[str]) -> tuple[int, bool]:
    points, intent_rules = rules["points"], rules["intent"]
    if not intent:
        reasons.append("Intent not provided — no intent-based scoring applied.")
        return 0, False
    lowered = intent.lower().strip()
    if lowered in [i.lower() for i in intent_rules["positive"]]:
        reasons.append(f"Customer expressed positive intent ({intent}).")
        return points["intent_positive"], False
    if lowered in [i.lower() for i in intent_rules["negative"]]:
        reasons.append(f"Customer expressed negative intent ({intent}).")
        return points["intent_negative"], True
    reasons.append(f"Customer intent ({intent}) is neutral/undecided.")
    return points["intent_neutral"], False


def score_lead(args: ScoreLeadArgs, rules: dict | None = None) -> ScoreLeadResult:
    rules = rules or load_rules()
    reasons: list[str] = []
    total = 0
    disqualified = False

    for points, is_disqualifier in (
        _score_age(args.age, rules, reasons),
        _score_budget(args.budget, rules, reasons),
        _score_family_size(args.family_size, rules, reasons),
        _score_conditions(args.conditions, rules, reasons),
        _score_intent(args.intent, rules, reasons),
    ):
        total += points
        disqualified = disqualified or is_disqualifier

    thresholds = rules["thresholds"]
    if disqualified:
        temperature = LeadTemperature.COLD
        reasons.append("Hard disqualifier present — classified cold regardless of total points.")
    elif total >= thresholds["hot_min_points"]:
        temperature = LeadTemperature.HOT
    elif total >= thresholds["warm_min_points"]:
        temperature = LeadTemperature.WARM
    else:
        temperature = LeadTemperature.COLD

    return ScoreLeadResult(temperature=temperature, points=total, reasons=reasons)
