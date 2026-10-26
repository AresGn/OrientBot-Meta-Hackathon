# OrientBot Agent (Meta Hackathon)

An agent that takes a post-BAC student's grade-sheet photo and voice message, chooses its own tools step by step, and produces a sourced orientation report for Benin.

> **Status: early scaffold.** The agent loop and two tools are skeletons; model-calling tools are not implemented yet.

## Problem

- TODO: sourced figures on post-BAC orientation in Benin (see `docs/impact.md`). No number is stated until a source is added.

## What is new in this repository

OrientBot already exists as a separate project. **No code from it is copied here.** Everything in this repository was written during the hackathon:

- the agentic loop (tool selection, execution, observation, next decision),
- the tools in `src/tools/`,
- the Meta API client,
- the evaluation cases in `evals/`,
- the sourced programs dataset (`data/filieres.csv`, currently empty/TODO).

## Demo

Video: TODO

## How the agent decides

```
input (text / photo / voice)
        │
        ▼
 model picks a tool ◄──────────┐
        │                      │
   run tool → observation ─────┘
        │ (enough info, or step limit)
        ▼
   build_report (cites sources)
```

Tools:

| Tool | Purpose | State |
|---|---|---|
| `transcribe_voice` | Transcribe a voice message | not implemented |
| `read_grade_sheet` | Read grades from a sheet photo | not implemented |
| `lookup_filieres` | Look up verified programs in `data/filieres.csv` | implemented, dataset TODO |
| `build_report` | Report where each recommendation cites its source | skeleton |

If an input is unreadable or a grade is missing, the agent is designed to ask rather than guess (not yet evaluated).

## Meta models used

| Task | Model | Role |
|---|---|---|
| Reasoning, tool choice, text | Muse Spark 1.3 | Agent brain |
| Grade-sheet reading | Muse Spark 1.3 (vision) | Extract grades from photos |
| Voice message transcription | Muse Voice Transcribe | Speech to text |

Tool calling support in Muse Spark 1.3 is **not yet confirmed** (see `docs/architecture.md`). There is no text-to-speech.

## Quick start

```bash
pip install -r requirements.txt
cp .env.example .env   # then set MUSE_API_KEY
python -m src.main     # currently exits: not implemented
```

## Evaluation

Cases in `evals/cases.jsonl`: blurry photo, missing grade, noisy voice message. Sample files are not created yet. Results: TODO (nothing measured).

## Limitations

- Agent is not functional end to end yet.
- Tool calling in Muse Spark 1.3 unverified.
- `data/filieres.csv` has no verified entries yet, so no recommendation can be produced.
- Only fictional sample data; no real-student testing.
- No voice output.

## Team

TODO: list all teammates.

## License

MIT, see `LICENSE`.
