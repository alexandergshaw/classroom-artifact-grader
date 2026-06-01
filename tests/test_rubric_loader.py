from pathlib import Path

from grader.rubric_loader import load_rubric


def test_load_rubric_example_assignment() -> None:
    rubric = load_rubric(Path("assignments/example-assignment"))
    assert rubric.assignment_id == "example-plugin-assignment"
    assert rubric.points_possible == 20
    assert len(rubric.checks) == 2
