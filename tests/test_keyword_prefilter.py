"""
Characterization tests for digest.keyword_prefilter.

Behaviour documented here reflects the function as written – these tests lock
in that behaviour so regressions are caught immediately.

Key notes on the fallback path
-------------------------------
If fewer than min(50, keep_top) items match *any* keyword the function falls
back to returning items[:keep_top] instead of the matched subset.  Tests that
need to verify rejection (case 3) must therefore supply enough matched items
(>= min(50, keep_top)) to force the non-fallback code path.
"""

import pytest
from digest import keyword_prefilter


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def paper(title: str = "", summary: str = "") -> dict:
    """Minimal item dict with just the fields keyword_prefilter reads."""
    return {"title": title, "summary": summary}


def _many_matched(keyword: str, n: int) -> list[dict]:
    """Return n items whose title contains *keyword*."""
    return [paper(title=f"{keyword} paper {i}") for i in range(n)]


# ---------------------------------------------------------------------------
# case 5 – empty items list → empty result
# ---------------------------------------------------------------------------

def test_empty_items_returns_empty_list():
    result = keyword_prefilter([], ["machine learning"], keep_top=10)
    assert result == []


def test_empty_items_with_no_keywords_returns_empty_list():
    result = keyword_prefilter([], [], keep_top=10)
    assert result == []


# ---------------------------------------------------------------------------
# case 1 – title match passes the filter
# ---------------------------------------------------------------------------

def test_title_match_is_included():
    item = paper(title="A survey of machine learning methods")
    # keep_top=1 → min(50,1)=1; matched=1; 1<1 is False → sort path used
    result = keyword_prefilter([item], ["machine learning"], keep_top=1)
    assert item in result


def test_title_match_exact_substring():
    item = paper(title="Attention is all you need")
    result = keyword_prefilter([item], ["attention"], keep_top=1)
    assert item in result


# ---------------------------------------------------------------------------
# case 2 – abstract / summary match passes the filter
# ---------------------------------------------------------------------------

def test_summary_match_is_included():
    item = paper(title="Some unrelated title", summary="We apply deep learning to NLP tasks.")
    result = keyword_prefilter([item], ["deep learning"], keep_top=1)
    assert item in result


def test_summary_match_when_title_has_no_keyword():
    item = paper(title="Paper about trees", summary="transformer architecture beats baselines")
    result = keyword_prefilter([item], ["transformer"], keep_top=1)
    assert item in result


# ---------------------------------------------------------------------------
# case 3 – no keyword match → item is rejected (non-fallback path)
# ---------------------------------------------------------------------------

def test_unmatched_item_is_rejected():
    # Provide 50 matched items so len(matched)=50 >= min(50,50)=50 → sort path
    keyword = "neural network"
    matched = _many_matched(keyword, 50)
    reject_me = paper(title="Unrelated article about gardening")
    all_items = matched + [reject_me]

    result = keyword_prefilter(all_items, [keyword], keep_top=50)

    assert reject_me not in result


def test_only_unmatched_items_triggers_fallback_not_rejection():
    """
    When *nothing* matches the fallback returns items[:keep_top], so the item
    is NOT filtered out.  This characterises the fallback behaviour explicitly.
    """
    item = paper(title="Cooking recipes and tips")
    result = keyword_prefilter([item], ["quantum computing"], keep_top=10)
    # fallback fires (0 matched < min(50,10)=10) → items[:10] returned
    assert item in result


# ---------------------------------------------------------------------------
# case 4 – matching is case-insensitive
# ---------------------------------------------------------------------------

def test_uppercase_title_matches_lowercase_keyword():
    item = paper(title="ADVANCES IN MACHINE LEARNING")
    result = keyword_prefilter([item], ["machine learning"], keep_top=1)
    assert item in result


def test_lowercase_title_matches_uppercase_keyword():
    item = paper(title="advances in machine learning")
    result = keyword_prefilter([item], ["MACHINE LEARNING"], keep_top=1)
    assert item in result


def test_mixed_case_in_summary_matches():
    item = paper(title="A new approach", summary="We study Large Language Models (LLMs).")
    result = keyword_prefilter([item], ["large language models"], keep_top=1)
    assert item in result


# ---------------------------------------------------------------------------
# additional characterisation – keep_top cap + ordering
# ---------------------------------------------------------------------------

def test_keep_top_limits_results():
    keyword = "ai"
    items = _many_matched(keyword, 100)
    result = keyword_prefilter(items, [keyword], keep_top=10)
    assert len(result) <= 10


def test_higher_hit_count_ranked_first():
    """Items matching more keywords appear before items matching fewer."""
    keyword_a = "reinforcement learning"
    keyword_b = "reward"
    # item_double matches both keywords (hits=2); item_single matches only one (hits=1)
    item_double = paper(title=f"{keyword_a}", summary=f"{keyword_b} shaping strategy")
    item_single = paper(title=f"{keyword_a} survey")

    # keep_top=3 → min(50,3)=3; pad 3 items so total matched=5 ≥ 3 → sort path taken
    pad = _many_matched(keyword_a, 3)
    all_items = [item_single] + pad + [item_double]

    result = keyword_prefilter(all_items, [keyword_a, keyword_b], keep_top=3)

    # After descending sort: item_double (2 hits) comes before item_single (1 hit)
    assert result.index(item_double) < result.index(item_single)
