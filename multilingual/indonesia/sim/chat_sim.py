"""Indonesia simulator CLI — `make multilingual-sim-id`. Defaults to an
in-process KB connection, same reasoning as the Philippines simulator
and voice_agent/sim/chat_sim.py.
"""

from __future__ import annotations

import argparse
import sys

from multilingual.common.chat_sim import run_all_scripted
from multilingual.common.settings import REPO_ROOT, get_settings
from multilingual.indonesia.app.tools import dispatch
from multilingual.indonesia.sim.scenarios import SCENARIOS

OUTPUT_DIR = REPO_ROOT / "recordings" / "multilingual" / "indonesia"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Indonesia voice bot simulator.")
    parser.add_argument("--scenario", default=None, help="Run only this scenario id.")
    args = parser.parse_args(argv)

    settings = get_settings()
    scenarios = [s for s in SCENARIOS if args.scenario in (None, s.scenario_id)]
    if not scenarios:
        print(f"No scenario with id {args.scenario!r}.", file=sys.stderr)
        return 1

    from fastapi.testclient import TestClient

    from kb.app.main import app as kb_app

    with TestClient(kb_app, base_url="http://kb.local") as kb_client:
        transcripts = run_all_scripted(
            scenarios, settings, dispatch, "indonesia", OUTPUT_DIR, kb_http_client=kb_client
        )
    for scenario_id in transcripts:
        print(f"{scenario_id}: transcript written to {OUTPUT_DIR / (scenario_id + '.md')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
