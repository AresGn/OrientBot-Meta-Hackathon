# PRD : OrientBot Agent (Meta Global AI Developer Hackathon)

**Piste :** Startup — prix visé : Best Agentic Use-Case
**Période de construction :** 26 octobre → 3 novembre 2026 (gel des fonctionnalités le 3 novembre)
**Soumission :** mercredi 4 novembre 2026, 21 h ET (= 5 novembre, 02 h 00 UTC ; l'heure à Porto-Novo est à revérifier, car ET passe à UTC-5 après le 1er novembre, soit 03 h 00 à Porto-Novo). Visée : soumettre le 3 novembre au soir.

---

## 1. Problème

Un bachelier béninois choisit sa filière souvent sur des critères flous (la série, l'avis de la famille, la rumeur). Il ne voit pas clairement quelles filières sont accessibles avec ses notes réelles, ni où trouver l'information officielle.

> **Règle du projet :** aucun chiffre n'entre dans le README, la vidéo ou la démo sans source officielle citée. Tant qu'une source manque, on écrit `TODO`.

## 2. Utilisateur et valeur

- **Utilisateur principal :** un bachelier (série C ou D au minimum pour la démo) qui envoie la photo de son relevé et un message vocal.
- **Valeur :** en quelques minutes, il reçoit une liste de filières compatibles avec ses notes, chacune avec sa source, et l'agent lui demande de corriger ce qu'il ne peut pas lire.
- **Pourquoi c'est un agent :** l'agent choisit lui-même l'outil suivant selon ce qu'il observe (audio à transcrire, photo illisible, profil incomplet). Un pipeline fixe ne suffit pas pour ce prix.

## 3. Objectifs mesurables (fin de hackathon)

| # | Objectif | Mesure |
|---|---|---|
| O1 | Un cas complet tourne de bout en bout | Relevé fictif → rapport sourcé, sans intervention humaine |
| O2 | L'agent ne devine pas | 0 note ou filière inventée dans les cas d'évaluation |
| O3 | Autonomie visible | Au moins 3 appels d'outils par cas, affichés dans la démo |
| O4 | Gestion de l'erreur | Au moins 1 cas où l'agent demande une nouvelle photo ou une confirmation |
| O5 | Reproductible | `evals/results/` contient les sorties brutes des tests |

## 4. Périmètre

### Dans le périmètre (à construire pendant l'événement)

- Boucle de l'agent : choix d'outil, exécution, observation, décision suivante, limite de 10 pas.
- `read_grade_sheet` : lecture d'un relevé photo (Muse Spark 1.3, vision) vers un JSON `{matiere, note}`.
- `transcribe_voice` : transcription d'un message vocal (Muse Voice Transcribe).
- `lookup_filieres` : recherche dans `data/filieres.csv`, lignes non vérifiées exclues.
- `build_report` : rapport où chaque recommandation cite sa ligne source.
- Interface web de démo (`web/`) : envoi photo + audio, affichage des étapes en direct, rapport final.
- Jeu d'évaluation : 5 cas (`evals/cases.jsonl`), résultats mesurés dans `evals/results/`.
- Données : 15 à 20 filières vérifiées pour une ou deux séries. Ce n'est pas une base nationale, et le README le dit.
- Vidéo de 3 minutes, README final, liste de l'équipe.

### Hors périmètre (explicitement)

- WhatsApp (connexion Baileys ou API officielle), paiement KKiaPay, landing page.
- Base de données, comptes utilisateurs, file de tâches.
- Synthèse vocale (l'API Meta n'en propose pas).
- Rapport audio pour les parents.
- Calcul de bourse et pipeline complet des garde-fous de recommandation de la V1.
- Questionnaire RIASEC complet.

Ce qui est repris de la V1 (règles uniquement) est détaillé dans `docs/v1-reuse.md`. Si une tâche hors périmètre semble indispensable, on le note dans `docs/decisions.md` et on ne l'implémente pas avant le 3 novembre.

## 5. Exigences fonctionnelles

**FR-1 Boucle agent.** L'agent reçoit l'entrée de l'élève, choisit l'outil suivant (Muse Spark 1.3 avec `tools`), exécute, observe, puis décide. Il s'arrête au bout de 10 pas.

**FR-2 Lecture de relevé.** La sortie est un JSON strict. Si une matière est illisible, la note est `null` et l'agent demande confirmation.

**FR-3 Transcription.** La sortie est un texte et un score de confiance si l'API le fournit. Sinon, l'agent demande confirmation des faits clés (série, moyenne).

**FR-4 Recherche de filières.** Entrées : série, moyenne calculée. Sortie : liste de lignes du CSV avec `source_status = verifie`, chacune avec `source_url`. Les autres lignes (`TODO`) sont exclues.

**FR-5 Rapport.** Chaque recommandation affiche sa filière, l'établissement, la condition d'accès et l'URL source. Si aucune ligne n'est disponible, le rapport le dit au lieu de recommander.

**FR-6 Démo web.** L'élève charge une photo et un audio. La page affiche chaque étape (outil, entrée, sortie) au fur et à mesure, puis le rapport.

**FR-7 Mode dégradé.** Si le réseau ou l'API échouent pendant la démo, la page affiche l'enregistrement de la dernière exécution réussie, avec la mention « exécution enregistrée ».

## 6. Exigences non fonctionnelles

- **Honnêteté :** le README, la vidéo et la démo ne décrivent que ce qui tourne réellement.
- **Données :** uniquement des relevés fictifs. Aucune donnée réelle d'élève, aucune donnée personnelle.
- **Secrets :** `MUSE_API_KEY` dans `.env` uniquement, jamais versionnée.
- **Accessibilité du dépôt :** le README s'ouvre sans être connecté, sans lien vers un dépôt privé.
- **Coût :** les tests restent sous les crédits de 150 $. Surveiller la facturation dans Billing.

## 7. Plan de travail (9 jours)

| Jour | Date | Livrable |
|---|---|---|
| J1 | Mar 27 | Test d'appel d'outils (fait) ; test vision avec une photo fictive |
| J2 | Mer 28 | `read_grade_sheet` implémenté ; test sur 2 relevés fictifs |
| J3 | Jeu 29 | `transcribe_voice` implémenté (endpoint vérifié dans la doc) |
| J4 | Ven 30 | `filieres.csv` : 15 lignes vérifiées avec `source_url` |
| J5 | Sam 31 | Boucle complète en CLI : relevé + audio → rapport sourcé |
| J6 | Dim 1 nov | Démo web branchée sur le serveur, affichage des étapes |
| J7 | Lun 2 nov | 5 cas d'évaluation, résultats commités, corrections |
| J8 | Mar 3 nov | Vidéo de 3 minutes, README final, équipe listée, **gel des fonctionnalités** |
| J9 | Mer 4 nov | Marge, soumission si ce n'est pas fait la veille |

**Équipe :** tous les coéquipiers doivent être inscrits sur la plateforme CV avant le 2 novembre. Poste sur `#team-search` si besoin.

## 8. Plan d'évaluation

| Cas | Entrée | Comportement attendu |
|---|---|---|
| `blurry_photo` | Photo floue | Demande une nouvelle photo, n'invente aucune note |
| `missing_grade` | Une matière absente | Signale la matière manquante, ne l'invente pas |
| `noisy_voice_message` | Message bruité | Demande confirmation des faits clés |
| `clear_sheet_c` | Relevé net, série C | Rapport avec filières sourcées |
| `no_match` | Moyenne très basse | Le rapport dit qu'aucune filière vérifiée ne correspond |

Critère de réussite : 4 cas sur 5 conformes, et 0 invention sur l'ensemble.

## 9. Risques et réponses

| Risque | Impact | Réponse |
|---|---|---|
| Appel d'outils instable en démo | Démo ratée | Test répété 5 fois (fait) ; enregistrement de secours |
| Vision peu fiable sur relevés manuscrits | Mauvaises notes | Commencer avec des relevés imprimés fictifs ; dire la limite dans le README |
| Filières vérifiées difficiles à trouver | Pas de recommandation | Limiter à 15 lignes, annoncer le périmètre, sourcer chaque ligne |
| Équipe pas à jour sur la plateforme | Soumission incomplète | Vérifier le 2 novembre au plus tard |
| Dérive de périmètre | Rien de fini | Gel le 3 novembre ; tout le reste va dans `docs/decisions.md` |
| Cadre « Startup » : code existant | Rejet | README : section « What is new » ; démo : seulement le travail de l'événement |

## 10. Démo et vidéo (3 min)

1. 0:00–0:30 : problème, avec une seule source citée.
2. 0:30–2:15 : relevé fictif + message vocal → l'agent enchaîne les outils seul, affichage des étapes.
3. 2:15–2:45 : cas difficile (photo floue) → l'agent demande au lieu de deviner.
4. 2:45–3:00 : ce qui est nouveau, limites, équipe.

## 11. Checklist de soumission

- [ ] Dépôt public, s'ouvre sans connexion
- [ ] README : statut réel, section « What is new », modèles Meta, limites, équipe
- [ ] Vidéo de 3 minutes (lien dans le README)
- [ ] `evals/results/` avec sorties brutes
- [ ] Aucune clé, aucun chemin personnel, aucune donnée réelle dans le dépôt
- [ ] Tous les coéquipiers listés sur la plateforme CV
- [ ] Soumission sur la plateforme CV avant le 4 novembre, 21 h ET
