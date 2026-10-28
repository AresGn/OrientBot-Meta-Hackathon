# Architecture

Document de conception de PathProof. Le comportement attendu est dans `docs/prd.md` ; ici, la structure technique. **Rien de ceci n'est encore implémenté de bout en bout** (voir la colonne « État »).

## Boucle de l'agent

```mermaid
flowchart TD
    IN([Student input: grade-sheet photo and voice note]) --> AGENT

    subgraph LOOP [Agent loop - max 12 steps]
        AGENT{{"Muse Spark 1.3<br/>chooses next action"}}
        AGENT -->|audio| T1[transcribe_voice]
        T1 --> T2[extract_profile]
        AGENT -->|image| T3[read_grade_sheet]
        AGENT -->|grades and profile known| T5[compute_ranking_average<br/>deterministic]
        T5 --> T6[lookup_filieres<br/>deterministic]
        AGENT -->|unreadable, missing, contradiction| ASK[ask_student<br/>pauses the loop]
        ASK --> AGENT
        T2 --> AGENT
        T3 --> AGENT
        T6 --> AGENT
    end

    AGENT -->|draft report with proofs| V[verify_report<br/>deterministic]
    V -->|problems found| AGENT
    V -->|all proven| B[build_report]
    AGENT -->|step limit reached| STOP([Stop: no report])
    B --> OUT([Report with proofs])
```

Limite de pas : 12 (`MAX_STEPS` dans `src/agent/loop.py`, PRD FR-1), comptés sur toute l'exécution : `steps_used` voyage dans l'état suspendu, reprises comprises. `ask_student` suspend la boucle : `run` renvoie `{status: needs_input, question, messages, tool_call_id, pending_tool_call_ids, steps_used}` sans aucun appel de modèle ni d'outil supplémentaire, puis `resume(client, model, tool_schemas, suspended, student_answer)` répond à **chaque** appel en attente du message suspendu — la réponse de l'élève pour `ask_student`, une erreur `not executed` pour les autres, jamais exécutés — comme messages `tool`, et relance la boucle (la vraie API refuse un historique où un `tool_call_id` reste sans réponse) ; une réponse vide renvoie le même état `needs_input` sans rien appeler, un état mal formé échoue franchement (clé manquante). Même mécanisme pour la CLI (stdin) et le web (événement `needs_input`, E5.1).

## Outils

| Outil | Rôle | Moteur | État |
|---|---|---|---|
| `transcribe_voice` | Transcrire la note vocale | Muse Voice Transcribe | implémenté (`src/tools/transcribe_voice.py`) ; sortie `{text, text_normalized, confidence}` (`text` tel qu'entendu, cité par E2.2 ; `text_normalized` avec les nombres en chiffres, `quatorze` → `14`, pour l'extraction ; `confidence` `None` tant que l'API n'en fournit pas, donc FR-4 s'applique) ; tout format accepté (`.flac`, `.m4a`, `.mp3`, `.ogg`, `.opus`, `.wav`, `.webm`) converti en WAV 24 kHz mono via ffmpeg (avec délai maximal), résultat vérifié (mono 16 bits, 10 min et 32 Mo au plus) avant tout appel ; biais `["série C", "série D", "SVT"]` ; `TranscriptionError` en cas d'échec, jamais un texte vide ; sorties brutes : `docs/spikes/voice/transcribe_voice/` |
| `extract_profile` | Série, moyenne déclarée, intérêts, métier, contraintes, avec citation exacte | Muse Spark 1.3 (JSON strict) | implémenté (`src/tools/extract_profile.py`) ; sortie `{serie_declaree, moyenne_declaree, interets, metier_vise, contraintes, flags}`, chaque champ gardé `{"value", "quote"}` avec `quote` copiée mot pour mot de la transcription (`text` de `transcribe_voice`) ; une citation absente ou inexacte rejette le champ par code (scalaire → `null`, élément de liste écarté), un champ non dit est `null` (liste vide), jamais une valeur par défaut ; valeurs déclarées gardées telles quelles, série hors C/D ou moyenne hors 0–20 signalée dans `flags` (`serie_non_prise_en_charge`, `moyenne_declaree_hors_plage`), jamais corrigée ; aucun filtrage (une ville dite reste une contrainte notée, PRD §2.1) ; `ProfileError` si le JSON est invalide, tronqué ou hors schéma ; appel réel sur la note cohérente : série D, 11,2, médecin, Cotonou (issue #16) |
| `read_grade_sheet` | Lire le relevé en `[{matiere, note, lisible}]` | Muse Spark 1.3 (vision) | implémenté (`src/tools/read_grade_sheet.py`) ; sortie `{serie, matieres: [{matiere, note, lisible, flags}], moyenne_affichee, flags}` (moyenne imprimée sur le relevé, copiée, jamais calculée), drapeaux `note_hors_plage`, `matiere_inconnue`, `serie_non_prise_en_charge`, `moyenne_hors_plage` ; `GradeSheetError` si le JSON est invalide, tronqué ou d'un type d'image non géré |
| `zoom_cell` | Isoler une cellule douteuse et la relire | SAM 3.1 + Muse Spark 1.3 | **abandonné** : NO GO au spike E0.6 (`docs/decisions.md`) ; l'agent demande une nouvelle photo |
| `compute_ranking_average` | Moyenne de classement d'une offre (formule page 8) | code | implémenté (`src/tools/compute_ranking_average.py`) |
| `lookup_filieres` | Filtrer les offres accessibles puis les classer | code | stub sur l'ancien schéma `filieres.csv`, à réécrire |
| `ask_student` | Poser une question, suspendre la boucle | interface | implémenté (`src/tools/ask_student.py` + suspension/reprise dans `src/agent/loop.py`) ; `ask_student(question)` valide par code (texte non vide, une seule question — un second « ? » est refusé, `AskStudentError`) et renvoie `{status: needs_input, question}` ; la question est rédigée en français par le modèle (prompt système, écart noté dans `docs/decisions.md`), une question invalide du modèle devient une observation d'erreur et ne suspend pas ; tests sans réseau : outil dans `tests/test_ask_student.py`, boucle dans `tests/test_loop.py` avec un faux client scripté et strict (`ScriptedFakeClient` dans `tests/fake_client.py`, qui refuse un `tool_call_id` sans réponse comme la vraie API) |
| `verify_report` | Contrôler chaque preuve du brouillon | code | implémenté (`src/tools/verify_report.py`) ; entrée `(report, context)` avec `context = {"serie", "grades", "transcript"}` (grades au format `read_grade_sheet(...)["matieres"]`), sortie liste de problèmes `{claim_id, type, reason}` vide si tout est prouvé ; `grade` comparée au relevé (matière normalisée, note égale, ligne lisible), `transcript` cherchée mot pour mot, `filiere` contrôlée dans `data/offres_publiques_2026_2027.csv` (ligne `Statut_qualité = OK`, `champ`/`valeur` égaux à la ligne) et `data/pages_offres.csv` (page égale), `calc` recalculée par `compute_ranking_average` depuis la série, les notes du contexte et les coefficients (formule, entrées et `moyenne_arrondie` comparés) ; problèmes de forme repris de `validate_report` ; échec fermé (rapport mal formé, contexte absent ou exception d'un contrôle = problème, jamais une liste vide) et refus sans valeur attendue (le résultat recalculé n'apparaît jamais dans une raison) ; aucun import SDK, aucun réseau |
| `build_report` | Mettre en forme le rapport validé | code | squelette |
| `run_vertical_slice` | Tranche verticale E2.5 : fixture JSON, calcul, recherche provisoire, brouillon avec preuves, `verify_report` | code | implémenté (`src/tools/run_vertical_slice.py`, `scripts/run_vertical_slice.py`) ; recherche provisoire = `Statut_qualité = OK` + `Bac_recommandé` et segment `Matières` simple, remplacée par E3.5 |

Briques du domaine (code pur, sans réseau) : `src/domain/coefficients.py` (`load_coefficients(serie)` : séries C et D, groupe 1, sans EPS), `src/domain/grade_scale.py` (`MIN_GRADE`, `MAX_GRADE`, `is_on_grade_scale` : échelle 0–20 partagée par `compute_ranking_average`, `read_grade_sheet` et `extract_profile`), `src/domain/subjects.py` (`normalize_subject(raw)` : `UnknownSubjectError` si la matière est inconnue) et `src/domain/proofs.py` (`SCHEMA_VERSION = 1`, `validate_proof`, `validate_report` : format des preuves figé au J2).

## Preuves et vérificateur

Le rapport est d'abord un JSON où chaque affirmation (`claim`) porte au moins une preuve. Le format est **figé** (E1.4, `SCHEMA_VERSION = 1` dans `src/domain/proofs.py`) : après le J2, il ne change plus sans une entrée dans `docs/decisions.md`.

| Type | Champs obligatoires | Référence contrôlée par `verify_report` |
|---|---|---|
| `grade` | `matiere` (texte), `note` (nombre) | la note lue sur la photo |
| `transcript` | `quote` (texte) | la citation existe mot pour mot dans la transcription |
| `filiere` | `offre_id` (texte), `page_pdf` (entier ≥ 1), `champ` (texte : colonne du CSV), `valeur` (texte ou nombre) | l'`Offre_ID` d'une ligne `Statut_qualité = OK`, sa page du PDF (`data/pages_offres.csv`) et la valeur annoncée dans la colonne |
| `calc` | `formula` (texte), `inputs` (liste non vide), `result` (nombre) | le résultat de `compute_ranking_average` (`moyenne_arrondie`), recalculé |

Chaque affirmation porte un `claim_id` (texte non vide, unique dans le rapport), un `text` et au moins une preuve. `validate_report` contrôle la forme (version du schéma, `claim_id`, texte, preuves, champs et types, entrées de `calc.inputs`, aucune clé inconnue (rapport, affirmation ou preuve) ni nombre non fini) et renvoie la liste des problèmes `{claim_id, type, reason}`, vide si tout est en règle (`type = structure` pour ces problèmes de forme, `claim_id` nul pour ceux du rapport entier). `verify_report` (E2.4) réutilise ces problèmes tels quels, puis vérifie que chaque référence existe et correspond : c'est du **code**, pas un second appel au modèle. Tant qu'il renvoie un problème, aucun rapport n'est affiché (FR-8).

Exemple de rapport complet :

```json
{
  "schema_version": 1,
  "claims": [
    {
      "claim_id": "svt-grade",
      "text": "SVT : 15/20 au relevé.",
      "proofs": [{"type": "grade", "matiere": "SVT", "note": 15}]
    },
    {
      "claim_id": "doctor-goal",
      "text": "Tu as dit vouloir être médecin (« peut-être médecin »).",
      "proofs": [{"type": "transcript", "quote": "peut-être médecin"}]
    },
    {
      "claim_id": "medecine-access",
      "text": "Médecine Générale (FSS) : 95 bourses prévues, moyenne de classement 13,15.",
      "proofs": [
        {"type": "filiere", "offre_id": "PUB-062", "page_pdf": 36, "champ": "Bourse", "valeur": 95},
        {"type": "calc", "formula": "M = Σ(mi·ci) / Σci",
         "inputs": [{"matiere": "SVT", "note": 15, "coefficient": 5},
                    {"matiere": "Mathématiques", "note": 12, "coefficient": 4},
                    {"matiere": "Sciences Physiques (PCT/SPCT)", "note": 12, "coefficient": 4}],
         "result": 13.15}
      ]
    }
  ]
}
```

## Données

| Fichier | Rôle |
|---|---|
| `data/offres_publiques_2026_2027.csv` | 224 offres ; source principale de `lookup_filieres` |
| `data/series_et_offres_2026_2027.csv` | 897 couples série–offre ; index par série |
| `data/controle_qualite_2026_2027.csv` | 39 anomalies ; section « Ce que je n'ai pas pu vérifier » |
| `data/pages_offres.csv` | offre → page du PDF officiel (brouillon : 19 à vérifier, 2 introuvables) |
| `data/coefficients_bac_benin.json` | coefficients du Bac par série (groupe 1) ; entrée de `compute_ranking_average` |
| `data/filieres.csv` | ancien gabarit vide, remplacé par les fichiers ci-dessus ; à supprimer avec la réécriture de `lookup_filieres` |

Le PDF du guide n'est pas versionné (`data/source/`, ignoré par git).

## Décisions

- Python, SDK OpenAI pointé sur `https://api.meta.ai/v1`.
- Pas de synthèse vocale (l'API Meta n'en propose pas).
- Accès strict (lignes `OK`, série dans `Bac_recommandé`, mode d'entrée affiché), classement expliqué. Détail : `docs/prd.md` section 3.
- Le modèle ne calcule jamais une moyenne ni un filtre : ce sont des outils déterministes.
- Aucune donnée réelle d'élève ; relevés et notes vocales fictifs uniquement.
- `MUSE_API_KEY` côté serveur uniquement, dans `.env`.

## Points à confirmer

- **Appel d'outils (function calling) de Muse Spark 1.3 : observé, non documenté.** `scripts/test_muse_tool_call.py` (rapport : `docs/muse-spark-tool-call-results.md`) montre 5 réussites sur 5 avec un seul outil `lookup_filieres` et une seule question. Le choix entre deux outils et le renvoi du résultat sont testés dans `docs/muse-spark-roundtrip-results.md` (5 sur 5) ; les appels enchaînés ne sont pas observés : le modèle demande les deux outils en parallèle dans un même tour, donc la boucle (E4.1) doit renvoyer un message `tool` par appel. La vision est testée dans le spike E0.4 (`docs/decisions.md`). Résultats rapportés, non rejoués par nous.
- **Muse Voice Transcribe** : relevé dans la doc officielle et testé en français (spike E0.5, voir `docs/decisions.md`). `muse-voice-transcribe-1.0`, `POST https://api.meta.ai/v1/asr/transcribe` en `multipart/form-data` (parties `request` JSON et `audio`), WAV mono PCM 16 bits à 16 ou 24 kHz uniquement, 10 min et 32 Mo au plus, aucun score de confiance.
- **Format d'envoi des images** : data URL base64 `image/jpeg` dans un message `image_url`, observé avec `muse-spark-1.3` (spike E0.4, `docs/spikes/vision/`). Taille maximale acceptée non trouvée dans la doc et non testée.
- **SAM 3.1** : testé (spike E0.6, `docs/spikes/sam/`). `sam-3.1` via `POST https://api.meta.ai/v1/responses` trouve le tableau (prompt « table »), jamais la cellule visée (0 sur 3, net et flou). NO GO : pas de `zoom_cell`.
