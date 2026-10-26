# Test Muse Spark 1.3 — appel d'outil `lookup_filieres`

Ce rapport vérifie que le modèle **choisit l'outil** proposé (pas la qualité de la réponse textuelle).

- **Date d'exécution :** 2026-10-26 16:51 UTC
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
| 1 | ✅ | `tool_calls` | `lookup_filieres` | `{"moyenne":13.5}` | Je vérifie les filières possibles avec 13,5. |
| 2 | ✅ | `tool_calls` | `lookup_filieres` | `{"moyenne":13.5}` | Je cherche les filières adaptées à 13,5. |
| 3 | ✅ | `tool_calls` | `lookup_filieres` | `{"moyenne":13.5}` | Je vérifie vos filières compatibles avec 13,5. |
| 4 | ✅ | `tool_calls` | `lookup_filieres` | `{"moyenne":13.5}` | Je vérifie les filières possibles avec 13,5. |
| 5 | ✅ | `tool_calls` | `lookup_filieres` | `{"moyenne":13.5}` | Je vais chercher les filières adaptées à votre moyenne de 13,5. |

## Détail brut (dernière exécution)

```
[ChatCompletionMessageFunctionToolCall(id='call_8c806033-ca1b-4077-9ef6-eb2a160b9fac', function=Function(arguments='{"moyenne":13.5}', name='lookup_filieres'), type='function')]
```

## Rejouer le test

```bash
python scripts/test_muse_tool_call.py
```

Prérequis : `MUSE_API_KEY` dans `.env` (voir `.env.example`).
