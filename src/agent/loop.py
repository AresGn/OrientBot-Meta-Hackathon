"""Agent loop: model picks a tool, we execute it, feed the observation back, repeat.

`ask_student` is the one tool that does not feed an observation back right
away: it suspends the loop, which returns {"status": "needs_input",
"question", "messages", "tool_call_id"} and makes no further model or tool
call. `resume` then appends the student's answer as the tool observation for
that call and continues the loop from the suspended messages.
"""
import json

from src.agent.prompts import SYSTEM_PROMPT
from src.tools.ask_student import ask_student
from src.tools.build_report import build_report
from src.tools.lookup_filieres import lookup_filieres
from src.tools.read_grade_sheet import read_grade_sheet
from src.tools.transcribe_voice import transcribe_voice

TOOLS = {
    "transcribe_voice": transcribe_voice,
    "read_grade_sheet": read_grade_sheet,
    "lookup_filieres": lookup_filieres,
    "ask_student": ask_student,
    "build_report": build_report,
}
MAX_STEPS = 12  # docs/prd.md FR-1


def run(client, model: str, tool_schemas: list[dict], user_input: str | None = None,
        *, messages: list | None = None, student_answer: str | None = None) -> str | dict:
    """Run the loop, or continue suspended `messages` when an answer is given.

    Returns the model's final text, or the `needs_input` dict of
    `ask_student` when the loop suspends. With `messages` and no answer, the
    suspended state is returned unchanged: no model or tool call is made.
    """
    if messages is not None:
        suspended = {"status": "needs_input", "question": _pending_question(messages),
                     "messages": messages, "tool_call_id": _pending_call_id(messages)}
        return resume(client, model, tool_schemas, suspended, student_answer)
    messages = [{"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_input}]
    return _continue_loop(client, model, tool_schemas, messages)


def resume(client, model: str, tool_schemas: list[dict], suspended: dict,
           student_answer: str | None) -> str | dict:
    """Resume a loop suspended by `ask_student` with the student's answer.

    The answer becomes the tool observation for the pending `ask_student`
    call, so the model sees it in `messages` like any other tool result. A
    blank answer resumes nothing: the same `needs_input` state is returned
    and neither the model nor any tool is called (ask, never guess).
    """
    messages = suspended["messages"]
    if not isinstance(student_answer, str) or not student_answer.strip():
        return {"status": "needs_input", "question": suspended["question"],
                "messages": messages, "tool_call_id": suspended.get("tool_call_id")}
    observation = json.dumps({"answer": student_answer.strip()}, ensure_ascii=False)
    messages.append({"role": "tool", "tool_call_id": suspended.get("tool_call_id"),
                     "content": observation})
    return _continue_loop(client, model, tool_schemas, messages)


def _continue_loop(client, model: str, tool_schemas: list[dict], messages: list) -> str | dict:
    for _ in range(MAX_STEPS):
        msg = client.chat.completions.create(
            model=model, messages=messages, tools=tool_schemas).choices[0].message
        messages.append(msg)
        if not msg.tool_calls:
            return msg.content or ""
        for call in msg.tool_calls:
            if call.function.name == "ask_student":
                suspended = _ask_student_suspension(call, messages)
                if suspended is not None:
                    return suspended
                continue
            messages.append(_tool_observation(call))
    return "Stopped: step limit reached."


def _ask_student_suspension(call, messages: list) -> dict | None:
    """Suspend on a valid question; an invalid one is an error observation."""
    try:
        result = ask_student(**json.loads(call.function.arguments))
    except Exception as error:  # tool error becomes an observation, not a crash
        messages.append({"role": "tool", "tool_call_id": call.id,
                         "content": json.dumps({"error": str(error)}, ensure_ascii=False)})
        return None
    return {**result, "messages": messages, "tool_call_id": call.id}


def _tool_observation(call) -> dict:
    try:
        result = TOOLS[call.function.name](**json.loads(call.function.arguments))
        content = json.dumps(result, default=str, ensure_ascii=False)
    except Exception as error:  # tool error becomes an observation, not a crash
        content = json.dumps({"error": str(error)}, ensure_ascii=False)
    return {"role": "tool", "tool_call_id": call.id, "content": content}


def _pending_call(messages: list):
    answered = {message.get("tool_call_id") for message in messages
                if isinstance(message, dict) and message.get("role") == "tool"}
    for message in reversed(messages):
        tool_calls = message.get("tool_calls") if isinstance(message, dict) \
            else getattr(message, "tool_calls", None)
        for call in tool_calls or []:
            if call.function.name == "ask_student" and call.id not in answered:
                return call
    return None


def _pending_call_id(messages: list) -> str | None:
    call = _pending_call(messages)
    return call.id if call is not None else None


def _pending_question(messages: list) -> str | None:
    call = _pending_call(messages)
    if call is None:
        return None
    try:
        return ask_student(**json.loads(call.function.arguments))["question"]
    except Exception:
        return None
