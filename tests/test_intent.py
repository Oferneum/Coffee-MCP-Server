"""
tests/test_intent.py — Intent router verification.

Compares the LLM router (`server._classify_intent`, gpt-4o-mini) against the
old keyword heuristic (`server._classify_intent_keyword`) on a set of tricky
queries chosen to expose where substring matching fails.

The headline pair:
    "how is decaf made"      → knowledge   (keyword wrongly says brewing)
    "how do I pull a 1:2 shot" → brewing    (both agree)
Same "how …" prefix, opposite intent — exactly the case a keyword scan can't
tell apart but the LLM can.

Run as a script (prints a side-by-side comparison table):
    python tests/test_intent.py

Run under pytest (asserts the LLM router label for each case):
    pytest tests/test_intent.py -v

Requires OPENAI_API_KEY (and the Supabase vars that server.py loads at import)
in the environment / .env. Without OPENAI_API_KEY the live LLM assertions are
skipped, because `_classify_intent` then degrades to the keyword fallback and
the comparison would be meaningless.
"""

import os
import sys

# Make the repo root importable when run from anywhere.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import server  # noqa: E402  (path setup must precede import)


# (query, expected_intent, why_it_is_tricky)
CASES: list[tuple[str, str, str]] = [
    # ── The headline contrast pair: same "how" prefix, opposite intent ──────────
    ("how is decaf made",
     "knowledge",
     'conceptual "how is X made" — keyword matches on bare "how" → brewing'),
    ("how do I pull a 1:2 shot",
     "brewing",
     'actionable "how do I…" for the user\'s own brew'),

    # ── Diagnosis with no defect keyword in the static map ──────────────────────
    ("this espresso tastes like ash",
     "diagnosis",
     'negative taste, but "ash" is in no keyword list → keyword defaults knowledge'),
    ("my v60 keeps coming out weak and watery",
     "diagnosis",
     '"weak"/"watery" are not in the negative-sensory set → keyword misses it'),

    # ── Recommendation phrased without the trigger words ────────────────────────
    ("what everyday bean should I grab without overspending",
     "recommendation",
     'buying intent with no "best/value/which bean" tokens → keyword → knowledge'),
    ("walk me through dialing in a new espresso",
     "brewing",
     'no how/brew/grind token present → keyword → knowledge'),

    # ── Cases the keyword method already gets right (regression guard) ──────────
    ("why does light roast taste more acidic",
     "knowledge",
     'explanatory "why does" — both methods agree'),
    ("is the pricey Gesha actually worth it",
     "recommendation",
     '"worth" token — both methods agree'),
]


def _has_openai_key() -> bool:
    return bool(os.environ.get("OPENAI_API_KEY"))


def _run_comparison() -> tuple[int, int, int]:
    """
    Print a side-by-side table and return
    (llm_correct, keyword_correct, fixed_by_llm) counts.
    `fixed_by_llm` = cases the keyword method got wrong but the LLM got right.
    """
    live = _has_openai_key()
    header = (
        f"{'QUERY':52s} {'EXPECTED':14s} "
        f"{'LLM':14s} {'KEYWORD':14s} VERDICT"
    )
    print(header)
    print("-" * len(header))

    llm_correct = keyword_correct = fixed = 0
    for query, expected, _why in CASES:
        keyword = server._classify_intent_keyword(query)
        llm = server._classify_intent(query) if live else "(skipped)"

        kw_ok = keyword == expected
        llm_ok = llm == expected
        keyword_correct += int(kw_ok)
        if live:
            llm_correct += int(llm_ok)
            if llm_ok and not kw_ok:
                fixed += 1

        if not live:
            verdict = "kw " + ("✓" if kw_ok else "✗")
        elif llm_ok and not kw_ok:
            verdict = "LLM FIXES IT"
        elif llm_ok and kw_ok:
            verdict = "both ✓"
        elif not llm_ok:
            verdict = "LLM ✗"
        else:
            verdict = ""

        print(f"{query[:52]:52s} {expected:14s} {llm:14s} {keyword:14s} {verdict}")

    print("-" * len(header))
    print(f"keyword correct : {keyword_correct}/{len(CASES)}")
    if live:
        print(f"LLM correct     : {llm_correct}/{len(CASES)}")
        print(f"fixed by LLM    : {fixed}  (keyword wrong → LLM right)")
    else:
        print("LLM correct     : (skipped — set OPENAI_API_KEY to run the router)")
    return llm_correct, keyword_correct, fixed


# ── pytest entry points ─────────────────────────────────────────────────────

def test_keyword_fallback_always_returns_valid_intent():
    """The deterministic fallback must never emit an out-of-vocab label."""
    for query, _expected, _why in CASES:
        assert server._classify_intent_keyword(query) in server._VALID_INTENTS


def test_llm_router_labels_match_expected():
    """The LLM router should classify each tricky query correctly."""
    if not _has_openai_key():
        try:
            import pytest
            pytest.skip("OPENAI_API_KEY not set — router falls back to keywords")
        except ImportError:
            print("SKIP: OPENAI_API_KEY not set")
            return
    failures = []
    for query, expected, _why in CASES:
        got = server._classify_intent(query)
        if got != expected:
            failures.append(f"{query!r}: expected {expected}, got {got}")
    assert not failures, "Router misclassified:\n  " + "\n  ".join(failures)


if __name__ == "__main__":
    llm_correct, keyword_correct, fixed = _run_comparison()
    # As a script, exit non-zero only when the live router underperforms the
    # keyword baseline — a meaningful regression signal in CI.
    if _has_openai_key() and llm_correct < keyword_correct:
        sys.exit(1)
