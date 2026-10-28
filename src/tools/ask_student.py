"""Ask the student one question and suspend the agent loop until the answer."""


class AskStudentError(ValueError):
    """The question cannot be asked as is; the model rephrases instead of guessing."""


def ask_student(question: str) -> dict:
    """Validate the single question the loop will surface to the student.

    Returns {"status": "needs_input", "question"}: this is an interface tool,
    so it displays and writes nothing itself. The loop (`src/agent/loop.py`)
    intercepts the call, returns that dict to the caller and makes no further
    model or tool call until `resume` feeds the student's answer back as a
    tool observation. The question is written by the model in French (see
    `src/agent/prompts.py`); the code only guarantees what it can check: a
    non-empty text, one question at a time (a second "?" is refused).
    """
    if not isinstance(question, str) or not question.strip():
        raise AskStudentError("ask_student question must be a non-empty text")
    question = question.strip()
    if question.count("?") > 1:
        raise AskStudentError("ask_student asks one question at a time")
    return {"status": "needs_input", "question": question}
