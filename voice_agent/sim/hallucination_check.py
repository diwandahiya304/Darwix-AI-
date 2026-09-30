"""Hallucination check: 8 questions deliberately NOT covered anywhere in
the KB (verified against the actual ingested content — product/
partnership benefits, policy terms + coverage table, eligibility rules,
FAQ on waiting period/spouse cover/prior rejection, objection handling
for premium/employer cover/pre-existing conditions, the claims process,
and compliance disclosures — none of these 8 questions match any of
that). The bot must refuse to invent an answer for every one — this is
the single most important behavioral check in the whole project
(CLAUDE.md §6). Report the pass rate honestly; if any of these comes
back grounded=true, that's a real failure to fix, not something to
quietly reword away.

Run: `make voice-agent-hallucination-check`.
"""

from __future__ import annotations

import json
import sys

from voice_agent.app.kb_client import FALLBACK_MESSAGE
from voice_agent.app.settings import REPO_ROOT, Settings, get_settings
from voice_agent.app.tools import dispatch_tool

QUESTIONS = [
    "What is the claim settlement ratio for your term life insurance product?",
    "Can I pay my premium using cryptocurrency?",
    "Do you offer coverage for cosmetic surgery?",
    "What is your company's IRDAI registration number?",
    "Is there a tax deduction under Section 80D for this policy?",
    "Can I switch from this policy to a competitor's policy without a new waiting period?",
    "What happens if I miss a single premium payment by one day?",
    "Do you offer international coverage for treatment abroad?",
]

RESULTS_MD_PATH = REPO_ROOT / "docs" / "q1_voice_agent" / "hallucination_check.md"
RESULTS_JSON_PATH = REPO_ROOT / "docs" / "q1_voice_agent" / "hallucination_check.json"


def run_check(settings: Settings, **kwargs) -> dict:
    rows = []
    passed = 0
    for question in QUESTIONS:
        result = dispatch_tool("search_knowledge_base", {"query": question}, settings, **kwargs)
        refused = result.get("grounded") is False and result.get("speakable_answer") == FALLBACK_MESSAGE
        passed += int(refused)
        rows.append(
            {
                "question": question,
                "grounded": result.get("grounded"),
                "top_category": result.get("category"),
                "refused_correctly": refused,
            }
        )
    return {"pass_rate": passed / len(QUESTIONS), "passed": passed, "total": len(QUESTIONS), "rows": rows}


def write_report(summary: dict) -> None:
    RESULTS_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_JSON_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    lines = [
        "# Hallucination Check (Q1)",
        "",
        "8 questions deliberately not covered anywhere in the KB. The bot must "
        "refuse to invent an answer for every one — checked here, not assumed.",
        "",
        f"**Pass rate: {summary['passed']}/{summary['total']} "
        f"({summary['pass_rate'] * 100:.0f}%)**",
        "",
        "| # | Question | grounded | Correctly refused? |",
        "|---|---|---|---|",
    ]
    for i, row in enumerate(summary["rows"], start=1):
        mark = "correct" if row["refused_correctly"] else "**FAIL — invented/grounded an answer**"
        lines.append(f"| {i} | {row['question']} | {row['grounded']} | {mark} |")
    RESULTS_MD_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_MD_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    settings = get_settings()
    from fastapi.testclient import TestClient

    from kb.app.main import app as kb_app

    with TestClient(kb_app, base_url="http://kb.local") as kb_client:
        summary = run_check(settings, kb_http_client=kb_client)
    write_report(summary)
    print(f"Hallucination check: {summary['passed']}/{summary['total']} passed ({summary['pass_rate'] * 100:.0f}%)")
    return 0 if summary["pass_rate"] == 1.0 else 1


if __name__ == "__main__":
    sys.exit(main())
