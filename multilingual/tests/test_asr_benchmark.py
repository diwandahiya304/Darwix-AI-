from multilingual.asr_bench.run_benchmark import run_benchmark
from multilingual.asr_bench.test_utterances import TEST_UTTERANCES


def test_run_benchmark_produces_one_row_per_utterance_per_fake_provider():
    summary = run_benchmark()
    # 2 fake providers per utterance
    assert len(summary["rows"]) == len(TEST_UTTERANCES) * 2


def test_run_benchmark_reports_real_providers_as_not_configured():
    summary = run_benchmark()
    assert "not configured" in summary["real_provider_status"]["deepgram-nova-3"]
    assert "not configured" in summary["real_provider_status"]["azure-speech"]


def test_loanword_drop_provider_produces_nonzero_wer_when_reference_has_loanwords():
    summary = run_benchmark()
    ph_cooperative_rows = [
        r for r in summary["rows"]
        if r["utterance_id"] == "ph_cooperative" and r["provider"] == "illustrative-loanword-drop-pattern"
    ]
    assert ph_cooperative_rows
    assert ph_cooperative_rows[0]["wer"] > 0
    assert ph_cooperative_rows[0]["code_switch_preserved"] is False


def test_regional_accent_utterance_is_covered():
    summary = run_benchmark()
    regional_rows = [r for r in summary["rows"] if r["category"] == "regional_accent"]
    assert len(regional_rows) == 2  # one per fake provider
    assert all(r["market"] == "indonesia" for r in regional_rows)
