from multilingual.asr_bench.metrics import (
    check_code_switching_handling,
    compute_wer_cer,
    named_term_accuracy,
)


def test_identical_text_has_zero_wer_and_cer():
    result = compute_wer_cer("kailan po ang due date", "kailan po ang due date")
    assert result.wer == 0.0
    assert result.cer == 0.0


def test_one_word_substitution_has_nonzero_wer():
    result = compute_wer_cer("kailan po ang due date ng premium", "kailan po ang due date ng preemium")
    assert result.wer > 0.0
    assert result.cer > 0.0


def test_named_term_accuracy_finds_and_misses_terms():
    result = named_term_accuracy(
        "ang premium po ay dapat bayaran bago mag lapse", ["premium", "lapse", "beneficiary"]
    )
    assert result.found_terms == ["premium", "lapse"]
    assert result.missed_terms == ["beneficiary"]
    assert result.accuracy == 2 / 3


def test_named_term_accuracy_with_no_expected_terms_returns_none():
    result = named_term_accuracy("some text", [])
    assert result.accuracy is None


def test_code_switching_preserved_when_all_markers_present():
    result = check_code_switching_handling(
        "cicilannya udah jatuh tempo, ada DP dan tenor",
        "cicilannya udah jatuh tempo, ada DP dan tenor",
        ["DP", "tenor"],
    )
    assert result.reference_has_code_switch is True
    assert result.hypothesis_preserved_switch_terms is True


def test_code_switching_flagged_when_markers_dropped_by_asr():
    result = check_code_switching_handling(
        "cicilannya udah jatuh tempo, ada DP dan tenor",
        "cicilannya udah jatuh tempo, ada di dan tena",  # ASR mangled DP/tenor
        ["DP", "tenor"],
    )
    assert result.reference_has_code_switch is True
    assert result.hypothesis_preserved_switch_terms is False
