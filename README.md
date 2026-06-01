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
- `grader/report_generator.py`: JSON + Markdown report output

## Supported file types

Current:
- ZIP
- TXT
- PDF
- DOCX

Future-ready placeholders:
- GitHub repository URLs
- Website URLs
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

```bash
python -m grader.main \
  --assignment assignments/example-assignment \
  --submission /absolute/path/to/submission.txt
```

Outputs:

- `reports/report.json`
- `reports/report.md`

## Interpreting reports

Reports include:
- assignment + submission metadata
- total score and points possible
- passed checks
- failed checks
- manual review items
- instructor notes section

## Assignment-specific plugins

Each assignment may optionally include:

```text
assignments/<assignment-id>/
  checks/
  feedback/
  validators/
```

- `checks/`: custom check handlers (e.g. `contains_student_name`)
- `validators/`: rubric validation hooks
- `feedback/`: report post-processing hooks

See `assignments/example-assignment` for a working plugin example.

## Running the Demo

The repository ships with a complete end-to-end demo that exercises every part
of the grading pipeline before you create real course assignments.

### What the demo includes

| Path | Description |
|---|---|
| `assignments/demo-assignment/rubric.yaml` | 100-point rubric covering all built-in check types |
| `assignments/demo-assignment/notes.md` | Instructor notes explaining the rubric |
| `submissions/excellent_submission.docx` | Passes every automated check (70/70) |
| `submissions/passing_submission.docx` | Passes heading and word-count checks (45/70) |
| `submissions/failing_submission.docx` | Passes only the citation check (5/70) |
| `scripts/run_demo.py` | Grades all three submissions and prints a summary |
| `tests/test_demo.py` | Automated validation of the demo pipeline |

### Running the demo script

```bash
python scripts/run_demo.py
```

Expected output (scores printed to stdout):

```
Submission                          Score (automated)
------------------------------------------------------------
excellent_submission.docx           70/70
passing_submission.docx             45/70
failing_submission.docx             5/70

Note: 30 manual-review points are excluded from the score above.
      An instructor must award those points after reviewing each submission.
```

### Generated files

After running the script, per-submission reports are written under
`reports/demo/<submission_stem>/`:

```
reports/demo/
├── excellent_submission/
│   ├── report.json
│   └── report.md
├── passing_submission/
│   ├── report.json
│   └── report.md
└── failing_submission/
    ├── report.json
    └── report.md
```

### How the scoring works

The demo rubric awards points across six checks:

| Check | Type | Points |
|---|---|---|
| `min_word_count` | `word_count` | 15 |
| `has_introduction_heading` | `heading_exists` | 15 |
| `has_reflection_heading` | `heading_exists` | 15 |
| `required_database_terms` | `required_terms` | 20 |
| `has_citations` | `citation_count` | 5 |
| `instructor_manual_review` | `manual` | 30 |

The first five checks are fully automated; the last one is flagged for
instructor review.  The automated maximum is therefore **70 points**.

### Why manual-review points are not automatically awarded

The `manual` check type is a deliberate placeholder.  It always returns
`passed=False` and `earned_points=0` during automated grading because the
grading engine has no way to evaluate subjective criteria such as writing
quality, originality, or depth of argument.  An instructor reads the
submission and enters the earned points separately.  The check appears in the
report under **Manual review items** so that instructors know exactly where
to record their feedback.

### Running the demo tests

```bash
python -m pytest tests/test_demo.py -v
```

## Extending with new checks

1. Add a deterministic check implementation in `grader/checks/` for framework-level checks, or
2. Add assignment-local plugins under `assignments/<assignment-id>/checks/` for custom logic.

No machine learning or LLM integration is used.
