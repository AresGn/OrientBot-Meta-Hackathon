"""Agent loop: model picks a tool, we execute it, feed the observation back, repeat.

`ask_student` is the one tool that does not feed an observation back right
away: it suspends the loop, which returns {"status": "needs_input",
"question", "messages", "tool_call_id", "pending_tool_call_ids",
"steps_used"} and makes no further model or tool call. `resume` then answers
every pending tool call of that message (the student's answer for
`ask_student`, a "not executed" error for the others, which the real API
requires before any new model call), appends them as tool observations and
continues the loop. Steps are counted across suspensions: `steps_used`
travels in the suspended state, so the 12-step limit (FR-1) covers the whole
run, resumes included.
"""
import json

from src.agent.prompts import SYSTEM_PROMPT
from src.tools.ask_student import ask_student
from src.tools.build_report import build_report
from src.tools.lookup_filieres import lookup_filieres
from src.tools.read_grade_sheet import read_grade_sheet
from src.tools.transcribe_voice import transcribe_voice

ASK_STUDENT_TOOL = "ask_student"
NOT_EXECUTED_ERROR = "not executed: answer the pending question first"
TOOLS = {
    "transcribe_voice": transcribe_voice,
    "read_grade_sheet": read_grade_sheet,
    "lookup_filieres": lookup_filieres,
    ASK_STUDENT_TOOL: ask_student,
    "build_report": build_report,
}
MAX_STEPS = 12  # docs/prd.md FR-1


def run(client, model: str, tool_schemas: list[dict], user_input: str) -> str | dict:
    """Run the loop from a student input.

    Returns the model's final text, or the `needs_input` dict of
    `ask_student` when the loop suspends (see `resume`).
    """
    messages = [{"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_input}]
    return _continue_loop(client, model, tool_schemas, messages, steps_used=0)


def resume(client, model: str, tool_schemas: list[dict], suspended: dict,
           student_answer: str | None) -> str | dict:
    """Resume a loop suspended by `ask_student` with the student's answer.

    Every pending tool call of the suspended message gets a tool response:
    the answer for `ask_student` (the model sees it like any other tool
    result), `NOT_EXECUTED_ERROR` for the others, which were never executed.
    A blank answer resumes nothing: the suspended state is returned as is and
    neither the model nor any tool is called (ask, never guess). A malformed
    state fails loudly (missing key), never a silent `tool_call_id: None`.
    """
    messages = suspended["messages"]
    if not isinstance(student_answer, str) or not student_answer.strip():
        return {"status": "needs_input", "question": suspended["question"],
                "messages": messages, "tool_call_id": suspended["tool_call_id"],
                "pending_tool_call_ids": suspended["pending_tool_call_ids"],
                "steps_used": suspended["steps_used"]}
    answer = json.dumps({"answer": student_answer.strip()}, ensure_ascii=False)
    not_executed = json.dumps({"error": NOT_EXECUTED_ERROR}, ensure_ascii=False)
    for call_id in suspended["pending_tool_call_ids"]:
        content = answer if call_id == suspended["tool_call_id"] else not_executed
        messages.append({"role": "tool", "tool_call_id": call_id, "content": content})
    return _continue_loop(client, model, tool_schemas, messages,
                          steps_used=suspended["steps_used"])


def _continue_loop(client, model: str, tool_schemas: list[dict], messages: list,
                   steps_used: int) -> str | dict:
    while steps_used < MAX_STEPS:
        msg = client.chat.completions.create(
            model=model, messages=messages, tools=tool_schemas).choices[0].message
        steps_used += 1
        messages.append(msg)
        if not msg.tool_calls:
            return msg.content or ""
        for index, call in enumerate(msg.tool_calls):
            if call.function.name == ASK_STUDENT_TOOL:
                suspended = _ask_student_suspension(call, msg.tool_calls[index:], messages, steps_used)
                if suspended is not None:
                    return suspended
                continue
            messages.append(_tool_observation(call))
    return "Stopped: step limit reached."


def _ask_student_suspension(call, remaining_calls: list, messages: list,
                            steps_used: int) -> dict | str | None:
    """Suspend on a valid question; an invalid one is an error observation.

    `remaining_calls` is the suspended call plus every later call of the same
    message: none of them was executed, and `resume` answers each of them.
    At the step limit there is nothing to resume, so the loop stops instead.
    """
    try:
        result = ask_student(**json.loads(call.function.arguments))
    except Exception:
        messages.append(_tool_observation(call))
        return None
    if steps_used >= MAX_STEPS:
        return "Stopped: step limit reached."
    return {**result, "messages": messages, "tool_call_id": call.id,
            "pending_tool_call_ids": [pending.id for pending in remaining_calls],
            "steps_used": steps_used}


def _tool_observation(call) -> dict:
    try:
        result = TOOLS[call.function.name](**json.loads(call.function.arguments))
        content = json.dumps(result, default=str, ensure_ascii=False)
    except Exception as error:  # tool error becomes an observation, not a crash
        content = json.dumps({"error": str(error)}, ensure_ascii=False)
    return {"role": "tool", "tool_call_id": call.id, "content": content}
