"""Philippines simulator CLI — `make multilingual-sim-ph`. Defaults to
an in-process KB connection (same reasoning as voice_agent/sim/
chat_sim.py: avoids silently degrading every KB lookup to "ungrounded"
if `make run-kb` wasn't started separately).
"""

from __future__ import annotations

import argparse
import sys

from multilingual.common.chat_sim import run_all_scripted
from multilingual.common.settings import REPO_ROOT, get_settings
from multilingual.philippines.app.tools import dispatch
from multilingual.philippines.sim.scenarios import SCENARIOS

OUTPUT_DIR = REPO_ROOT / "recordings" / "multilingual" / "philippines"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Philippines voice bot simulator.")
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
            scenarios, settings, dispatch, "philippines", OUTPUT_DIR, kb_http_client=kb_client
        )
    for scenario_id in transcripts:
        print(f"{scenario_id}: transcript written to {OUTPUT_DIR / (scenario_id + '.md')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
