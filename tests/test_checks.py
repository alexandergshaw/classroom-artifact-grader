from grader.checks.document_checks import heading_exists
from grader.checks.text_checks import citation_count, word_count
from grader.models import Check


def test_word_count_passes_when_minimum_met() -> None:
    check = Check(id="wc", type="word_count", points=5, min=3)
    result = word_count(check, "one two three")
    assert result.passed is True
    assert result.earned_points == 5


def test_heading_exists_detects_heading_list() -> None:
    check = Check(id="h1", type="heading_exists", points=4, heading="Reflection")
    result = heading_exists(check, text="", headings=["Introduction", "Reflection"])
    assert result.passed is True


def test_citation_count_uses_deterministic_patterns() -> None:
    check = Check(id="c1", type="citation_count", points=6, min=2)
    text = "This is supported (Smith, 2024). Another source [1]."
    result = citation_count(check, text)
    assert result.passed is True
    assert result.earned_points == 6
