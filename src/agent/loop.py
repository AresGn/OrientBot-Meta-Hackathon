"""Agent loop: model picks a tool, we execute it, feed the observation back, repeat."""
import json

from src.agent.prompts import SYSTEM_PROMPT
from src.tools.build_report import build_report
from src.tools.lookup_filieres import lookup_filieres
from src.tools.read_grade_sheet import read_grade_sheet
from src.tools.transcribe_voice import transcribe_voice

TOOLS = {
    "transcribe_voice": transcribe_voice,
    "read_grade_sheet": read_grade_sheet,
    "lookup_filieres": lookup_filieres,
    "build_report": build_report,
}
MAX_STEPS = 10


def run(client, model: str, tool_schemas: list[dict], user_input: str) -> str:
    """Untested skeleton. Tool calling was observed on a single-tool test only (see docs/)."""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user_input}]
    for _ in range(MAX_STEPS):
        msg = client.chat.completions.create(model=model, messages=messages, tools=tool_schemas).choices[0].message
        messages.append(msg)
        if not msg.tool_calls:
            return msg.content or ""
        for call in msg.tool_calls:
            result = TOOLS[call.function.name](**json.loads(call.function.arguments))
            messages.append({"role": "tool", "tool_call_id": call.id, "content": json.dumps(result, default=str)})
    return "Stopped: step limit reached."
