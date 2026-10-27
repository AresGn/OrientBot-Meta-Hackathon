# Test Muse Spark 1.3 — aller-retour avec deux outils

Vérifie que le modèle choisit le bon outil, reçoit son résultat en message `tool`, puis l'utilise dans sa réponse finale. Complète `docs/muse-spark-tool-call-results.md` (premier appel seulement). Les valeurs renvoyées sont fictives et impossibles à deviner.

- **Date d'exécution :** 2026-10-27 18:53 UTC
- **Modèle :** `muse-spark-1.3` — `max_tokens` = 4000
- **Outils exposés :** `get_filiere_cutoff` (renvoie 13.87), `get_bursary_amount` (renvoie 417)

## Synthèse

| Critère | Résultat |
| --- | --- |
| Aller-retour, bon outil + valeur dans la réponse finale | **5/5** |
| Choix de l'autre outil (bourse), 1 exécution | ✅ |
| Question sans outil : aucun appel, 1 exécution | ✅ |
| Appels enchaînés (question à deux outils) | demandés en parallèle dans un seul tour (pas d'enchaînement) ; réponse contenant les deux valeurs : ✅ |

## Coût

Tokens consommés au total : 10466 en entrée, 3780 en sortie (8 conversations). Le tarif en crédits n'est pas relevé par ce script : le coût en crédits n'est donc pas chiffré ici.

## Limites de ce test

- Deux outils seulement, une question par outil ; 5 essais pour l'aller-retour, 1 seul pour chacun des autres cas : ce n'est pas une mesure statistique.
- Valeurs d'outils fixes ; le test ne couvre ni les erreurs d'outil ni les arguments invalides.
- Les outils réels de PathProof (`lookup_filieres`...) ne sont pas testés ici.

## Sorties brutes

### Aller-retour, exécution 1

- Question : Quel est le seuil de moyenne de classement pour la filière Médecine ?
- Outils appelés : ['get_filiere_cutoff']
- Tokens : 1391 en entrée, 516 en sortie
- Résultat : ✅

```json
[
  {
    "finish_reason": "tool_calls",
    "content": "Je recherche le seuil pour la filière Médecine.",
    "tool_calls": [
      {
        "name": "get_filiere_cutoff",
        "arguments": "{\"filiere\":\"Médecine\"}"
      }
    ]
  },
  {
    "finish_reason": "stop",
    "content": "Le seuil de moyenne de classement pour la filière **Médecine** est de **13.87**.",
    "tool_calls": []
  }
]
```

### Aller-retour, exécution 2

- Question : Quel est le seuil de moyenne de classement pour la filière Médecine ?
- Outils appelés : ['get_filiere_cutoff']
- Tokens : 1391 en entrée, 448 en sortie
- Résultat : ✅

```json
[
  {
    "finish_reason": "tool_calls",
    "content": "Je recherche le seuil pour la filière Médecine.",
    "tool_calls": [
      {
        "name": "get_filiere_cutoff",
        "arguments": "{\"filiere\":\"Médecine\"}"
      }
    ]
  },
  {
    "finish_reason": "stop",
    "content": "Le seuil de moyenne de classement pour la filière **Médecine** est de **13.87**.\n",
    "tool_calls": []
  }
]
```

### Aller-retour, exécution 3

- Question : Quel est le seuil de moyenne de classement pour la filière Médecine ?
- Outils appelés : ['get_filiere_cutoff']
- Tokens : 1394 en entrée, 512 en sortie
- Résultat : ✅

```json
[
  {
    "finish_reason": "tool_calls",
    "content": "Je récupère le seuil de moyenne pour la filière Médecine.",
    "tool_calls": [
      {
        "name": "get_filiere_cutoff",
        "arguments": "{\"filiere\":\"Médecine\"}"
      }
    ]
  },
  {
    "finish_reason": "stop",
    "content": "Le seuil de moyenne de classement pour la filière **Médecine** est de **13.87**.",
    "tool_calls": []
  }
]
```

### Aller-retour, exécution 4

- Question : Quel est le seuil de moyenne de classement pour la filière Médecine ?
- Outils appelés : ['get_filiere_cutoff']
- Tokens : 1391 en entrée, 482 en sortie
- Résultat : ✅

```json
[
  {
    "finish_reason": "tool_calls",
    "content": "Je recherche le seuil de la filière Médecine.",
    "tool_calls": [
      {
        "name": "get_filiere_cutoff",
        "arguments": "{\"filiere\":\"Médecine\"}"
      }
    ]
  },
  {
    "finish_reason": "stop",
    "content": "Le seuil de moyenne de classement pour la filière **Médecine** est de **13.87**.",
    "tool_calls": []
  }
]
```

### Aller-retour, exécution 5

- Question : Quel est le seuil de moyenne de classement pour la filière Médecine ?
- Outils appelés : ['get_filiere_cutoff']
- Tokens : 1392 en entrée, 438 en sortie
- Résultat : ✅

```json
[
  {
    "finish_reason": "tool_calls",
    "content": "Je récupère le seuil pour la filière Médecine.",
    "tool_calls": [
      {
        "name": "get_filiere_cutoff",
        "arguments": "{\"filiere\":\"Médecine\"}"
      }
    ]
  },
  {
    "finish_reason": "stop",
    "content": "Le seuil de moyenne de classement pour la filière **Médecine** est de **13.87**.",
    "tool_calls": []
  }
]
```

### Autre outil (bourse)

- Question : Quel est le montant mensuel de la bourse pour la série D ?
- Outils appelés : ['get_bursary_amount']
- Tokens : 1372 en entrée, 493 en sortie
- Résultat : ✅

```json
[
  {
    "finish_reason": "tool_calls",
    "content": "Je recherche le montant pour la série D.",
    "tool_calls": [
      {
        "name": "get_bursary_amount",
        "arguments": "{\"serie\":\"D\"}"
      }
    ]
  },
  {
    "finish_reason": "stop",
    "content": "Le montant mensuel de la bourse pour la série D est de **417 FCFA**.",
    "tool_calls": []
  }
]
```

### Question sans outil

- Question : Combien font 7 fois 8 ?
- Outils appelés : aucun
- Tokens : 622 en entrée, 301 en sortie
- Résultat : ✅

```json
[
  {
    "finish_reason": "stop",
    "content": "7 fois 8 font **56**.",
    "tool_calls": []
  }
]
```

### Appels enchaînés

- Question : Donne-moi le seuil de moyenne de classement de Médecine ET le montant mensuel de la bourse pour la série D.
- Outils appelés : ['get_filiere_cutoff', 'get_bursary_amount']
- Tokens : 1513 en entrée, 590 en sortie
- Résultat : ✅

```json
[
  {
    "finish_reason": "tool_calls",
    "content": "Je récupère le seuil Médecine et la bourse série D.",
    "tool_calls": [
      {
        "name": "get_filiere_cutoff",
        "arguments": "{\"filiere\":\"Médecine\"}"
      },
      {
        "name": "get_bursary_amount",
        "arguments": "{\"serie\":\"D\"}"
      }
    ]
  },
  {
    "finish_reason": "stop",
    "content": "- **Seuil de moyenne de classement de Médecine :** **13.87**\n- **Montant mensuel de la bourse pour la série D :** **417 FCFA**",
    "tool_calls": []
  }
]
```

## Rejouer

```bash
python scripts/test_muse_roundtrip.py
```
