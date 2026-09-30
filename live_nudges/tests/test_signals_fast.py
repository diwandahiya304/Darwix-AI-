from live_nudges.app.models import Speaker, SignalType, TranscriptSegment
from live_nudges.app.settings import Settings
from live_nudges.app.signals_fast import SignalExtractor


def _segment(segment_id: int, speaker: Speaker, text: str, window_end_ms: int = 0, is_final: bool = True) -> TranscriptSegment:
    return TranscriptSegment(
        segment_id=segment_id, speaker=speaker, text=text, is_final=is_final,
        window_start_ms=max(0, window_end_ms - 1000), window_end_ms=window_end_ms, asr_latency_ms=100.0,
    )


def _extractor() -> SignalExtractor:
    return SignalExtractor(Settings())


def test_missed_cross_sell_fires_when_agent_closes_without_offering():
    extractor = _extractor()
    extractor.process(_segment(0, Speaker.AGENT, "Hi, calling about renewal.", 0))
    extractor.process(_segment(1, Speaker.CUSTOMER, "My spouse has been asking about coverage too.", 1000))
    signals = extractor.process(_segment(2, Speaker.AGENT, "Is there anything else I can help with?", 2000))
    assert any(s.topic == "missed_cross_sell:family_floater" for s in signals)


def test_cross_sell_not_flagged_once_agent_offers_the_relevant_plan():
    extractor = _extractor()
    extractor.process(_segment(0, Speaker.CUSTOMER, "My spouse has been asking about coverage too.", 0))
    extractor.process(_segment(1, Speaker.AGENT, "We do have a family floater plan that covers your spouse.", 1000))
    signals = extractor.process(_segment(2, Speaker.AGENT, "Is there anything else I can help with?", 2000))
    assert not any(s.topic == "missed_cross_sell:family_floater" for s in signals)


def test_risky_guarantee_statement_triggers_compliance_signal():
    extractor = _extractor()
    signals = extractor.process(_segment(0, Speaker.AGENT, "This plan offers guaranteed returns.", 0))
    assert any(s.signal_type == SignalType.COMPLIANCE_RISK and s.topic == "compliance:risky_statement" for s in signals)


def test_missing_disclosure_triggers_compliance_signal_at_closing():
    extractor = _extractor()
    extractor.process(_segment(0, Speaker.AGENT, "Your premium this year is 14500 rupees.", 0))
    signals = extractor.process(_segment(1, Speaker.AGENT, "Shall I proceed with the payment now?", 1000))
    assert any(s.topic == "compliance:missing_disclosure" for s in signals)


def test_disclosure_given_prevents_missing_disclosure_signal():
    extractor = _extractor()
    extractor.process(_segment(0, Speaker.AGENT, "Note there is a free-look period of 15 days.", 0))
    signals = extractor.process(_segment(1, Speaker.AGENT, "Shall I proceed with the payment now?", 1000))
    assert not any(s.topic == "compliance:missing_disclosure" for s in signals)


def test_rising_frustration_needs_two_hits_within_the_window():
    extractor = _extractor()
    signals_1 = extractor.process(_segment(0, Speaker.CUSTOMER, "I already told you I'm not interested.", 0))
    assert not any(s.signal_type == SignalType.FRUSTRATION for s in signals_1)
    signals_2 = extractor.process(_segment(1, Speaker.CUSTOMER, "How many times do I have to say this.", 1000))
    assert any(s.signal_type == SignalType.FRUSTRATION for s in signals_2)


def test_buying_signal_keyword_detected():
    extractor = _extractor()
    signals = extractor.process(_segment(0, Speaker.CUSTOMER, "Sounds good, sign me up.", 0))
    assert any(s.signal_type == SignalType.BUYING_SIGNAL for s in signals)


def test_callback_needed_keyword_detected():
    extractor = _extractor()
    signals = extractor.process(_segment(0, Speaker.CUSTOMER, "Can you call back tomorrow, not a good time.", 0))
    assert any(s.signal_type == SignalType.CALLBACK_NEEDED for s in signals)


def test_payment_difficulty_keyword_detected():
    extractor = _extractor()
    signals = extractor.process(_segment(0, Speaker.CUSTOMER, "I lost my job and can't afford this right now.", 0))
    assert any(s.signal_type == SignalType.PAYMENT_DIFFICULTY for s in signals)


def test_ambiguous_filler_speech_produces_no_signals():
    extractor = _extractor()
    signals = extractor.process(_segment(0, Speaker.CUSTOMER, "Umm, yeah, sort of, who is this again?", 0))
    assert signals == []


def test_partial_segments_are_ignored():
    extractor = _extractor()
    signals = extractor.process(_segment(0, Speaker.AGENT, "This plan offers guaranteed returns.", 0, is_final=False))
    assert signals == []


def test_empty_text_produces_no_signals():
    extractor = _extractor()
    signals = extractor.process(_segment(0, Speaker.CUSTOMER, "", 0))
    assert signals == []
