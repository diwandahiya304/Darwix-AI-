from multilingual.common.register import Register, detect_register


def test_filipino_formal_markers_detected():
    assert detect_register("Meron po ba kayong impormasyon, Ma'am?", "fil") == Register.FORMAL


def test_filipino_colloquial_markers_detected():
    assert detect_register("Ano ba, grabe naman ang bayad, pre.", "fil") == Register.COLLOQUIAL


def test_indonesian_formal_markers_detected():
    assert detect_register("Selamat siang, Bapak, mohon informasinya.", "id") == Register.FORMAL


def test_indonesian_colloquial_markers_detected():
    assert detect_register("Halo Kak, cicilannya udah jatuh tempo nih.", "id") == Register.COLLOQUIAL


def test_ambiguous_utterance_defaults_to_formal():
    assert detect_register("Baik, terima kasih.", "id") == Register.FORMAL


def test_custom_default_is_respected_when_ambiguous():
    assert detect_register("Baik, terima kasih.", "id", default=Register.COLLOQUIAL) == Register.COLLOQUIAL


def test_unknown_language_falls_back_to_default_with_no_markers():
    assert detect_register("Bonjour", "fr") == Register.FORMAL
