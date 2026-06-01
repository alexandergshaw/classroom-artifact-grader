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

## Extending with new checks

1. Add a deterministic check implementation in `grader/checks/` for framework-level checks, or
2. Add assignment-local plugins under `assignments/<assignment-id>/checks/` for custom logic.

No machine learning or LLM integration is used.
