"""Test the full tool round trip with Muse Spark 1.3: choice, tool result returned, final answer.

Writes docs/muse-spark-roundtrip-results.md (never docs/muse-spark-tool-call-results.md).
Usage: python scripts/test_muse_roundtrip.py
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = ROOT / "docs" / "muse-spark-roundtrip-results.md"
MODEL = "muse-spark-1.3"
MAX_TOKENS = 4000  # reasoning tokens count against the limit (AGENTS.md, section Modèle et API)
MAX_STEPS = 5
ROUNDTRIP_RUNS = 5  # docs/backlog.md E0.7

# Fictional values, deliberately odd so the model cannot guess them.
CUTOFF_VALUE = 13.87
BURSARY_VALUE = 417
TOOL_RESULTS = {
    "get_filiere_cutoff": {"filiere": "Médecine", "seuil_moyenne_classement": CUTOFF_VALUE},
    "get_bursary_amount": {"serie": "D", "montant_mensuel_fcfa": BURSARY_VALUE},
}

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_filiere_cutoff",
            "description": "Renvoie le seuil de moyenne de classement d'une filière.",
            "parameters": {
                "type": "object",
                "properties": {"filiere": {"type": "string"}},
                "required": ["filiere"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_bursary_amount",
            "description": "Renvoie le montant mensuel de la bourse pour une série du BAC.",
            "parameters": {
                "type": "object",
                "properties": {"serie": {"type": "string"}},
                "required": ["serie"],
            },
        },
    },
]

ROUNDTRIP_QUESTION = "Quel est le seuil de moyenne de classement pour la filière Médecine ?"
BURSARY_QUESTION = "Quel est le montant mensuel de la bourse pour la série D ?"
NO_TOOL_QUESTION = "Combien font 7 fois 8 ?"
CHAINED_QUESTION = (
    "Donne-moi le seuil de moyenne de classement de Médecine ET le montant mensuel "
    "de la bourse pour la série D."
)


def run_conversation(client: OpenAI, question: str) -> dict:
    """Run the tool loop until the model answers without tool call; return a raw trace."""
    messages: list[dict] = [{"role": "user", "content": question}]
    trace: dict = {"question": question, "steps": [], "tools_called": [], "usage": []}
    for _ in range(MAX_STEPS):
        response = client.chat.completions.create(
            model=MODEL, messages=messages, tools=TOOLS, max_tokens=MAX_TOKENS
        )
        choice = response.choices[0]
        message = choice.message
        trace["usage"].append(response.usage.model_dump() if response.usage else {})
        trace["steps"].append(
            {
                "finish_reason": choice.finish_reason,
                "content": message.content,
                "tool_calls": [
                    {"name": tc.function.name, "arguments": tc.function.arguments}
                    for tc in (message.tool_calls or [])
                ],
            }
        )
        if not message.tool_calls:
            trace["final_answer"] = message.content or ""
            return trace
        messages.append(message.model_dump(exclude_none=True))
        for tool_call in message.tool_calls:
            trace["tools_called"].append(tool_call.function.name)
            result = TOOL_RESULTS.get(tool_call.function.name, {"erreur": "outil inconnu"})
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result, ensure_ascii=False),
                }
            )
    trace["final_answer"] = ""
    trace["error"] = f"no final answer after {MAX_STEPS} steps"
    return trace


def contains_value(text: str, value: float | int) -> bool:
    """Accept both '13.87' and '13,87'; spaces in thousands are ignored."""
    compact = text.replace(" ", "").replace(" ", "").replace(" ", "")
    return str(value) in compact or str(value).replace(".", ",") in compact


def total_tokens(trace: dict) -> tuple[int, int]:
    prompt = sum(u.get("prompt_tokens", 0) for u in trace["usage"])
    completion = sum(u.get("completion_tokens", 0) for u in trace["usage"])
    return prompt, completion


def safe_run(client: OpenAI, question: str) -> dict:
    try:
        return run_conversation(client, question)
    except Exception as exc:  # recorded in the report, not hidden
        return {"question": question, "steps": [], "tools_called": [], "usage": [],
                "final_answer": "", "error": f"{type(exc).__name__}: {exc}"}


def evaluate(client: OpenAI) -> dict:
    roundtrip = [safe_run(client, ROUNDTRIP_QUESTION) for _ in range(ROUNDTRIP_RUNS)]
    for trace in roundtrip:
        trace["ok"] = (
            trace["tools_called"] == ["get_filiere_cutoff"]
            and contains_value(trace["final_answer"], CUTOFF_VALUE)
        )
    bursary = safe_run(client, BURSARY_QUESTION)
    bursary["ok"] = (
        bursary["tools_called"] == ["get_bursary_amount"]
        and contains_value(bursary["final_answer"], BURSARY_VALUE)
    )
    no_tool = safe_run(client, NO_TOOL_QUESTION)
    no_tool["ok"] = not no_tool["tools_called"] and "56" in no_tool["final_answer"]
    chained = safe_run(client, CHAINED_QUESTION)
    chained["ok"] = (
        set(chained["tools_called"]) == {"get_filiere_cutoff", "get_bursary_amount"}
        and contains_value(chained["final_answer"], CUTOFF_VALUE)
        and contains_value(chained["final_answer"], BURSARY_VALUE)
    )
    return {"roundtrip": roundtrip, "bursary": bursary, "no_tool": no_tool, "chained": chained}


def describe_chain(trace: dict) -> str:
    """Whether the tools were called in two separate model turns (true chaining) or in parallel."""
    turns_with_tools = [s for s in trace["steps"] if s["tool_calls"]]
    if len(turns_with_tools) >= 2:
        return "observés à la suite (tours distincts)"
    if turns_with_tools and len(turns_with_tools[0]["tool_calls"]) >= 2:
        return "demandés en parallèle dans un seul tour (pas d'enchaînement)"
    return "non observés"


def render_trace(title: str, trace: dict) -> list[str]:
    prompt, completion = total_tokens(trace)
    lines = [
        f"### {title}",
        "",
        f"- Question : {trace['question']}",
        f"- Outils appelés : {trace['tools_called'] or 'aucun'}",
        f"- Tokens : {prompt} en entrée, {completion} en sortie",
        f"- Résultat : {'✅' if trace.get('ok') else '❌'}"
        + (f" — erreur : `{trace['error']}`" if trace.get("error") else ""),
        "",
        "```json",
        json.dumps(trace["steps"], ensure_ascii=False, indent=2),
        "```",
        "",
    ]
    return lines


def render_report(results: dict) -> str:
    roundtrip = results["roundtrip"]
    passed = sum(1 for t in roundtrip if t["ok"])
    all_traces = roundtrip + [results["bursary"], results["no_tool"], results["chained"]]
    prompt = sum(total_tokens(t)[0] for t in all_traces)
    completion = sum(total_tokens(t)[1] for t in all_traces)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# Test Muse Spark 1.3 — aller-retour avec deux outils",
        "",
        "Vérifie que le modèle choisit le bon outil, reçoit son résultat en message `tool`, "
        "puis l'utilise dans sa réponse finale. Complète `docs/muse-spark-tool-call-results.md` "
        "(premier appel seulement). Les valeurs renvoyées sont fictives et impossibles à deviner.",
        "",
        f"- **Date d'exécution :** {stamp}",
        f"- **Modèle :** `{MODEL}` — `max_tokens` = {MAX_TOKENS}",
        f"- **Outils exposés :** `get_filiere_cutoff` (renvoie {CUTOFF_VALUE}), "
        f"`get_bursary_amount` (renvoie {BURSARY_VALUE})",
        "",
        "## Synthèse",
        "",
        "| Critère | Résultat |",
        "| --- | --- |",
        f"| Aller-retour, bon outil + valeur dans la réponse finale | **{passed}/{len(roundtrip)}** |",
        f"| Choix de l'autre outil (bourse), 1 exécution | {'✅' if results['bursary']['ok'] else '❌'} |",
        f"| Question sans outil : aucun appel, 1 exécution | {'✅' if results['no_tool']['ok'] else '❌'} |",
        f"| Appels enchaînés (question à deux outils) | {describe_chain(results['chained'])} ; "
        f"réponse contenant les deux valeurs : {'✅' if results['chained']['ok'] else '❌'} |",
        "",
        "## Coût",
        "",
        f"Tokens consommés au total : {prompt} en entrée, {completion} en sortie "
        f"({len(all_traces)} conversations). Le tarif en crédits n'est pas relevé par ce "
        "script : le coût en crédits n'est donc pas chiffré ici.",
        "",
        "## Limites de ce test",
        "",
        f"- Deux outils seulement, une question par outil ; {ROUNDTRIP_RUNS} essais pour l'aller-retour, "
        "1 seul pour chacun des autres cas : ce n'est pas une mesure statistique.",
        "- Valeurs d'outils fixes ; le test ne couvre ni les erreurs d'outil ni les arguments invalides.",
        "- Les outils réels de PathProof (`lookup_filieres`...) ne sont pas testés ici.",
        "",
        "## Sorties brutes",
        "",
    ]
    for index, trace in enumerate(roundtrip, start=1):
        lines += render_trace(f"Aller-retour, exécution {index}", trace)
    lines += render_trace("Autre outil (bourse)", results["bursary"])
    lines += render_trace("Question sans outil", results["no_tool"])
    lines += render_trace("Appels enchaînés", results["chained"])
    lines += ["## Rejouer", "", "```bash", "python scripts/test_muse_roundtrip.py", "```", ""]
    return "\n".join(lines)


def main() -> int:
    load_dotenv(ROOT / ".env")
    if not os.environ.get("MUSE_API_KEY"):
        raise SystemExit("MUSE_API_KEY is not set (see .env)")
    client = OpenAI(
        api_key=os.environ["MUSE_API_KEY"],
        base_url=os.environ.get("MUSE_BASE_URL", "https://api.meta.ai/v1"),
    )
    results = evaluate(client)
    OUT_PATH.write_text(render_report(results), encoding="utf-8")
    passed = sum(1 for t in results["roundtrip"] if t["ok"])
    print(f"Round trip: {passed}/{ROUNDTRIP_RUNS}; report: {OUT_PATH}")
    return 0 if passed == ROUNDTRIP_RUNS else 1


if __name__ == "__main__":
    sys.exit(main())
