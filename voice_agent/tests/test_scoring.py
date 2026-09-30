from voice_agent.app.models import LeadTemperature, ScoreLeadArgs
from voice_agent.app.scoring import score_lead


def test_ideal_candidate_scores_hot():
    args = ScoreLeadArgs(
        age=35, city="Mumbai", family_size=4, conditions=None, budget=2000, intent="interested"
    )
    result = score_lead(args)
    assert result.temperature == LeadTemperature.HOT
    assert result.points >= 3
    assert result.reasons


def test_marginal_candidate_scores_warm():
    # age=60 (senior, 0pts) + budget=1500 (comfortable, +1pt) + family_size=1 (0pts)
    # + intent=exploring (neutral, 0pts) = 1 point, at the warm threshold.
    args = ScoreLeadArgs(age=60, family_size=1, budget=1500, intent="exploring")
    result = score_lead(args)
    assert result.temperature == LeadTemperature.WARM


def test_underage_is_hard_disqualified_to_cold_even_with_generous_budget():
    args = ScoreLeadArgs(age=16, budget=5000, intent="interested", family_size=5)
    result = score_lead(args)
    assert result.temperature == LeadTemperature.COLD
    assert any("outside the standard insurable range" in r for r in result.reasons)


def test_budget_too_low_is_hard_disqualified():
    args = ScoreLeadArgs(age=30, budget=200, intent="interested")
    result = score_lead(args)
    assert result.temperature == LeadTemperature.COLD


def test_negative_intent_is_hard_disqualified():
    args = ScoreLeadArgs(age=30, budget=2000, family_size=4, intent="not_interested")
    result = score_lead(args)
    assert result.temperature == LeadTemperature.COLD


def test_red_flag_condition_penalizes_but_does_not_hard_disqualify():
    args = ScoreLeadArgs(age=35, budget=2000, family_size=4, intent="interested", conditions="history of cancer")
    result = score_lead(args)
    # Would be hot without the red flag; with it, still not cold (still insurable).
    assert result.temperature != LeadTemperature.COLD
    assert any("red-flag" in r for r in result.reasons)


def test_neutral_condition_does_not_penalize():
    with_condition = score_lead(
        ScoreLeadArgs(age=35, budget=2000, family_size=4, intent="interested", conditions="controlled diabetes")
    )
    without_condition = score_lead(
        ScoreLeadArgs(age=35, budget=2000, family_size=4, intent="interested")
    )
    assert with_condition.points == without_condition.points


def test_all_missing_fields_does_not_crash_and_is_cold():
    result = score_lead(ScoreLeadArgs())
    assert result.temperature == LeadTemperature.COLD
    assert result.points == 0
    assert len(result.reasons) == 5  # exactly one reason per scored dimension
