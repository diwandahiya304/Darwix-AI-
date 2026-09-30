import time

import pytest
import soundfile as sf
from fastapi.testclient import TestClient

import live_nudges.app.main as main_module
from live_nudges.app.audio_io import resample_linear
from live_nudges.audio_gen.tts import synthesize_line


@pytest.fixture
def short_wav(tmp_path):
    samples, sr = synthesize_line("Hi there.", voice_index=0)
    samples = resample_linear(samples, sr, 16000)
    path = tmp_path / "a_short_scenario.wav"
    sf.write(str(path), samples, 16000)
    return path


@pytest.fixture(autouse=True)
def _isolated_state(monkeypatch, tmp_path):
    monkeypatch.setattr(main_module, "_AUDIO_DIR", tmp_path)
    monkeypatch.setattr(main_module, "_running_call_id", None)
    yield


def test_health_endpoint():
    client = TestClient(main_module.app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_dashboard_serves_html():
    client = TestClient(main_module.app)
    response = client.get("/")
    assert response.status_code == 200
    assert "live_nudges" in response.text.lower()


def test_scenarios_lists_available_wav_stems(short_wav):
    client = TestClient(main_module.app)
    response = client.get("/scenarios")
    assert response.json() == ["a_short_scenario"]


def test_start_missing_scenario_returns_404():
    client = TestClient(main_module.app)
    response = client.post("/start", json={"scenario_id": "does_not_exist"})
    assert response.status_code == 404


def test_start_existing_scenario_returns_200_and_second_concurrent_start_is_rejected(short_wav):
    client = TestClient(main_module.app)
    response = client.post("/start", json={"scenario_id": "a_short_scenario", "speed": 1000.0})
    assert response.status_code == 200
    assert response.json()["status"] == "started"

    response_2 = client.post("/start", json={"scenario_id": "a_short_scenario", "speed": 1000.0})
    assert response_2.status_code == 409

    # let the background thread finish so it doesn't leak into other tests
    for _ in range(100):
        if main_module._running_call_id is None:
            break
        time.sleep(0.2)
