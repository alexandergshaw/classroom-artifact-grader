# classroom-artifact-grader

A deterministic, rubric-driven Python grading engine for classroom artifacts.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Architecture overview

- `grader/main.py`: CLI entrypoint and grading orchestration
- `grader/models.py`: Pydantic models (`Rubric`, `Check`, `CheckResult`, `GradeReport`)
- `grader/rubric_loader.py`: rubric.yaml loading and validation
- `grader/extractors/`: artifact-type extraction modules
- `grader/checks/`: deterministic check implementations
- `grader/plugin_loader.py`: assignment-specific plugin loading
- `grader/feedback_engine.py`: deterministic feedback generation from failed checks
- `grader/batch_grader.py`: production batch grading for entire submission directories
- `grader/report_generator.py`: JSON + Markdown + review form report output

## Supported file types

- ZIP
- TXT
- PDF
- DOCX
- PPTX
- XLSX

## Supported checks

- `file_exists`
- `folder_exists`
- `word_count`
- `heading_exists`
- `required_terms`
- `citation_count`
- `regex_contains`
- `text_contains`
- `manual`

## Creating new rubrics

Use `templates/rubric.yaml` as a starter and place assignment rubrics in:

```text
assignments/<assignment-id>/rubric.yaml
```

## Running the grader

### Single submission

```bash
python -m grader.main \
  --assignment assignments/example-assignment \
  --submission /absolute/path/to/submission.txt
```

Outputs per-submission:

- `reports/report.json`
- `reports/report.md`
- `reports/review_form.md`

### Batch grading (entire class)

```bash
python -m grader.main \
  --assignment assignments/databases-assignment-01 \
  --submission-dir path/to/student/submissions \
  --output-dir reports
```

Outputs:

```
reports/
└── databases-assignment-01/
    ├── student1/
    │   ├── report.json
    │   ├── report.md
    │   └── review_form.md
    ├── student2/
    │   └── ...
    ├── gradebook.csv
    ├── summary.json
    └── instructor_summary.md
```

## Plugin Architecture

Each assignment can define custom grading logic in its own directory without
modifying the core engine.

### Directory layout

```text
assignments/
└── databases-assignment-01/
    ├── rubric.yaml
    ├── checks/
    │   ├── __init__.py
    │   └── custom_checks.py     ← custom check handlers
    ├── validators/
    │   └── custom_validators.py ← rubric validation hooks
    └── feedback/
        ├── feedback_hooks.py    ← post-grading report hooks
        └── feedback_rules.yaml  ← feedback message overrides
```

### Registering custom checks

```python
# assignments/my-assignment/checks/custom_checks.py
from grader.models import Check, CheckResult

def check_my_custom_type(check: Check, context: dict) -> CheckResult:
    passed = "magic word" in context["text"].lower()
    return CheckResult(
        id=check.id, type=check.type,
        passed=passed,
        earned_points=check.points if passed else 0,
        possible_points=check.points,
        feedback="Found." if passed else "Not found.",
    )

def register_checks() -> dict:
    return {"my_custom_type": check_my_custom_type}
```

Then reference it in `rubric.yaml`:

```yaml
checks:
  - id: my_check
    type: my_custom_type
    points: 10
```

### Registering custom validators

```python
# assignments/my-assignment/validators/custom_validators.py
from grader.models import Rubric

def validate_something(rubric: Rubric) -> None:
    if rubric.points_possible < 10:
        raise ValueError("Rubric must have at least 10 points.")

def register_validators() -> list:
    return [validate_something]
```

### Registering feedback hooks

```python
# assignments/my-assignment/feedback/feedback_hooks.py
from grader.models import GradeReport

def add_custom_note(report: GradeReport) -> None:
    if not report.instructor_notes:
        report.instructor_notes = "Review before releasing grades."

def register_feedback() -> list:
    return [add_custom_note]
```

### Plugin failure isolation

If any plugin module fails to import or raises at runtime, the error is logged
and grading continues with all other checks.  A single broken plugin never
aborts an entire batch run.

## Feedback Rules

The feedback engine generates human-readable messages from failed checks using
a YAML rules file.

### Default rules

`templates/feedback_rules.yaml` maps each built-in check type to a failure
message:

```yaml
word_count:
  fail: "Submission does not meet the minimum word count requirement."

citation_count:
  fail: "Additional citations are required to support your claims."
```

### Assignment-specific overrides

Place `feedback_rules.yaml` inside the assignment's `feedback/` directory to
override the default messages for specific check types:

```yaml
# assignments/databases-assignment-01/feedback/feedback_rules.yaml
erd_mentioned:
  fail: "Your submission should include a discussion of an Entity-Relationship Diagram (ERD)."
```

Feedback messages are deduplicated: if multiple failed checks map to the same
message, it appears only once in the report.

## Instructor Review Process

Every graded submission gets a `review_form.md` alongside `report.json` and
`report.md`.

### review_form.md structure

- **Auto Score Summary** – automated score vs. points possible
- **Rubric Breakdown** – passed and failed checks with evidence
- **Automated Feedback** – deduplicated feedback from the feedback engine
- **Manual Review Sections** – one section per manual check with a space to
  enter points awarded and notes
- **Instructor Notes** – instructor-populated field
- **Final Score** – template for entering the final grade

### Workflow

1. Run the grader (single or batch)
2. Open `review_form.md` for each submission
3. Fill in the manual review sections and instructor notes
4. Record the final score

## Report Structure

### report.json

```json
{
  "assignment_id": "databases-assignment-01",
  "submission_path": "submissions/student1.docx",
  "total_score": 55.0,
  "points_possible": 100.0,
  "passed_checks": [...],
  "failed_checks": [...],
  "manual_review_items": [...],
  "feedback": ["Additional citations are required."],
  "instructor_notes": ""
}
```

### gradebook.csv

One row per submission with columns:

| Column | Description |
|---|---|
| `submission_name` | Filename |
| `assignment_id` | Assignment identifier |
| `auto_score` | Automated points earned |
| `auto_points_possible` | Total automated points available |
| `manual_points_available` | Points reserved for instructor review |
| `final_points_possible` | Total points on rubric |
| `passed_checks` | Count of passed checks |
| `failed_checks` | Count of failed checks |
| `manual_checks` | Count of manual-review checks |
| `status` | `success` or `error` |
| `error_message` | Error details (empty on success) |
| `report_path` | Path to per-submission report directory |

### summary.json

Aggregate statistics for the batch:

```json
{
  "total_submissions": 30,
  "successful_submissions": 28,
  "failed_submissions": 2,
  "average_auto_score": 54.3,
  "median_auto_score": 57.0,
  "highest_auto_score": 70.0,
  "lowest_auto_score": 20.0,
  "pass_rate": 0.714
}
```

### instructor_summary.md

A human-readable dashboard for the instructor:

- **Assignment Summary** – total, average, median, high, low scores
- **Common Failed Checks** – ranked list of which checks failed most
- **Manual Review Required** – submissions with manual-review items
- **Grading Warnings** – submissions with extraction or plugin failures

## Batch Grading Workflow

```bash
# 1. Grade entire class directory
python -m grader.main \
  --assignment assignments/databases-assignment-01 \
  --submission-dir submissions/databases-assignment-01 \
  --output-dir reports

# 2. Open the instructor dashboard
open reports/databases-assignment-01/instructor_summary.md

# 3. Open gradebook for export to LMS
open reports/databases-assignment-01/gradebook.csv

# 4. Review each submission's review form
open reports/databases-assignment-01/student1/review_form.md
```

The batch grader:
- Recursively discovers all supported file types (`.txt`, `.docx`, `.pdf`,
  `.zip`, `.pptx`, `.xlsx`) under the submission directory
- Grades each submission independently
- Never aborts the entire batch because one submission fails
- Logs individual failures with full error messages

## Running the Demo

The repository ships with a complete end-to-end demo.

### Running the demo script

```bash
python scripts/run_demo.py
```

Expected output:

```
Submission                          Score (automated)
------------------------------------------------------------
excellent_submission.docx           70/70
passing_submission.docx             45/70
failing_submission.docx             5/70

Note: 30 manual-review points are excluded from the score above.
      An instructor must award those points after reviewing each submission.
```

### Running the tests

```bash
python -m pytest tests/ -v
```

## Extending with new checks

1. Add a deterministic check implementation in `grader/checks/` for
   framework-level checks, or
2. Add assignment-local plugins under `assignments/<assignment-id>/checks/`
   for custom logic.

No machine learning or LLM integration is used.

