# Test Muse Spark 1.3 — appel d'outil `lookup_filieres`

Ce rapport vérifie que le modèle **choisit l'outil** proposé (pas la qualité de la réponse textuelle).

- **Date d'exécution :** 2026-10-26 16:54 UTC
- **Modèle :** `muse-spark-1.3`
- **Endpoint :** `https://api.meta.ai/v1`
- **Exécutions :** 5
- **Réussites :** 5/5

## Critères de réussite

- `finish_reason` = `tool_calls`
- `tool_calls[0].function.name` = `lookup_filieres`
- Arguments JSON contenant `moyenne` = **13.5** (virgule française dans la question)

## Résultats

| Run | OK | finish_reason | Outil | Arguments | content |
| ---: | :---: | --- | --- | --- | --- |
| 1 | ✅ | `tool_calls` | `lookup_filieres` | `{"moyenne":13.5}` | Je regarde les filières accessibles avec 13,5. |
| 2 | ✅ | `tool_calls` | `lookup_filieres` | `{"moyenne":13.5}` | Je vérifie les filières accessibles avec 13,5. |
| 3 | ✅ | `tool_calls` | `lookup_filieres` | `{"moyenne":13.5}` | Je vérifie les filières accessibles avec 13,5. |
| 4 | ✅ | `tool_calls` | `lookup_filieres` | `{"moyenne":13.5}` | Je vérifie les filières adaptées à 13,5. |
| 5 | ✅ | `tool_calls` | `lookup_filieres` | `{"moyenne":13.5}` | Je vérifie quelles filières correspondent à 13,5. |

## Sortie console brute (5 exécutions)

```text
=== Run 1 ===
finish_reason: tool_calls
tool_calls: [ChatCompletionMessageFunctionToolCall(id='call_a34b1621-8b30-4312-8fe9-39e6c13dafce', function=Function(arguments='{"moyenne":13.5}', name='lookup_filieres'), type='function')]
content: Je regarde les filières accessibles avec 13,5.

=== Run 2 ===
finish_reason: tool_calls
tool_calls: [ChatCompletionMessageFunctionToolCall(id='call_c5e0a220-62fc-489d-a271-434ac3667513', function=Function(arguments='{"moyenne":13.5}', name='lookup_filieres'), type='function')]
content: Je vérifie les filières accessibles avec 13,5.

=== Run 3 ===
finish_reason: tool_calls
tool_calls: [ChatCompletionMessageFunctionToolCall(id='call_04d60a59-c9c8-4b49-b974-ff02a2b30c7c', function=Function(arguments='{"moyenne":13.5}', name='lookup_filieres'), type='function')]
content: Je vérifie les filières accessibles avec 13,5.

=== Run 4 ===
finish_reason: tool_calls
tool_calls: [ChatCompletionMessageFunctionToolCall(id='call_190e4307-039e-491d-8dd1-ed429ece991f', function=Function(arguments='{"moyenne":13.5}', name='lookup_filieres'), type='function')]
content: Je vérifie les filières adaptées à 13,5.

=== Run 5 ===
finish_reason: tool_calls
tool_calls: [ChatCompletionMessageFunctionToolCall(id='call_da504829-261f-43b5-8455-b027f7924575', function=Function(arguments='{"moyenne":13.5}', name='lookup_filieres'), type='function')]
content: Je vérifie quelles filières correspondent à 13,5.
```

## Rejouer le test

```bash
python scripts/test_muse_tool_call.py
```

Prérequis : `MUSE_API_KEY` dans `.env` (voir `.env.example`).
