# AGENTS.md — règles de travail sur PathProof

Valable pour toute personne ou tout agent qui modifie ce dépôt. Court exprès : si une règle n'est pas ici, suivre le code voisin.

## Sources de vérité (dans cet ordre)
1. `docs/prd.md` : ce qu'on construit et ce qu'on ne construit pas.
2. `docs/backlog.md` : la story en cours, son critère d'acceptation, ses dépendances.
3. `docs/architecture.md` : outils, format des preuves, données.
4. `docs/decisions.md` : écarts au PRD. Toute idée hors périmètre y est notée, jamais implémentée avant le gel du 3 novembre.

En cas de conflit entre le code et le PRD, on ne tranche pas en silence : on le note dans `docs/decisions.md`.

## Règles du produit (non négociables)
- **Le modèle ne calcule pas.** Moyennes, filtres, vérification : du code déterministe, appelé comme outil.
- **Aucune affirmation sans preuve.** Chaque phrase du rapport porte une preuve (`grade`, `transcript`, `filiere`, `calc`) que `verify_report` contrôle.
- **Demander plutôt que deviner.** Note illisible, hors de 0–20, matière invalide, contradiction : `ask_student`, jamais une valeur par défaut.
- **Seules les lignes `Statut_qualité = OK`** sont recommandées. Pas de chances d'admission, pas de ville, pas de chiffre absent du guide.
- **Données fictives uniquement.** Aucune donnée réelle d'élève, nulle part.
- **Aucun code de la V1.** On ré-implémente des règles publiques (`docs/v1-reuse.md`), on ne copie rien.
- **Honnêteté.** README, vidéo et démo ne décrivent que ce qui tourne. Le mot « vérifié » n'apparaît qu'après l'audit de `docs/data-audit.md`. Le mot « chatbot » n'apparaît ni dans le README ni dans l'interface.

## Structure
```
src/agent/     boucle (loop.py) et prompt système ; ne contient AUCUNE logique métier
src/domain/    règles métier pures (coefficients, normalisation des matières, preuves) ; aucun réseau, aucun SDK
src/tools/     un outil = un module = une fonction publique (même nom que l'outil)
src/clients/   accès à l'API Meta ; seul endroit qui connaît le SDK et les paramètres du modèle
src/api/       serveur de démo (FastAPI) ; aucune logique métier
web/           interface statique
data/          sources de données, en lecture seule pour le code
tests/         un fichier test_<module>.py par module de src/
evals/         cas d'évaluation et résultats bruts ; lancés à la main
```
- Un outil prend et renvoie des **données** (dict, liste, dataclass), il n'affiche rien et n'écrit rien.
- Les outils déterministes (`compute_ranking_average`, `lookup_filieres`, `verify_report`, `build_report`) n'importent ni le SDK ni le réseau ; ils s'appuient sur `src/domain/`.
- La boucle ne fait que : demander un outil au modèle, l'exécuter, renvoyer le résultat. Une erreur d'outil devient une observation, pas un plantage.
- Entrées/sorties (fichiers, réseau, console) aux bords ; logique pure au centre.

## Nommage
- **Fichiers et modules :** `snake_case`, nommés d'après ce qu'ils font : `compute_ranking_average.py`, pas `utils.py` ni `helpers.py`.
- **Fonctions :** verbe + objet (`read_grade_sheet`, `normalize_subject`, `parse_subjects_by_series`). Le nom d'un outil est le nom de sa fonction.
- **Booléens :** `is_`, `has_`, `can_`. **Constantes :** `UPPER_SNAKE` avec un commentaire sur la source (`MAX_STEPS = 12  # docs/prd.md FR-1`).
- **Tests :** `test_<comportement attendu>` (`test_todo_rows_are_excluded`), pas `test_1`.
- **Langue :** anglais pour le code, les docstrings et les messages de commit. Le **vocabulaire du domaine** garde les mots français des données : `serie`, `filiere`, `matiere`, `note`, `moyenne`, `offre`. Un concept = un mot, partout (jamais `track` ici et `serie` là).
- Pas d'abréviation, sauf celles du domaine : `PCT`, `SVT`, `MESRS`, `FPP`.
- Colonnes des CSV du guide (`Offre_ID`, `Statut_qualité`...) : citées telles quelles, jamais renommées dans les fichiers de `data/`.

## Code propre
- Une fonction = une responsabilité, lisible d'un coup d'œil (ordre de grandeur : 30 lignes). Si elle fait « et », la couper.
- Annotations de type partout sur les signatures publiques (`str | None`, `list[dict]`), comme dans le code actuel.
- Pas de nombre magique : constante nommée, avec sa source (page du guide, article de l'arrêté).
- Pas de variable globale modifiable. Pas de code commenté. Pas de `print` de débogage commité.
- Les commentaires expliquent **pourquoi** (source, piège connu), pas ce que fait la ligne.
- Erreurs explicites : exception ou résultat typé avec une raison (« non calculé : coefficient manquant »). Jamais `except: pass`, jamais une valeur par défaut qui masque un manque.
- Pas d'abstraction avant le deuxième usage réel. On a 9 jours : la solution la plus simple qui satisfait le critère d'acceptation.
- Suivre le style voisin (formatage, imports, docstrings courtes) plutôt que d'en introduire un nouveau.

## Développer une feature
1. Prendre **une story** de `docs/backlog.md`. Pas de travail hors backlog sans l'ajouter d'abord.
2. Écrire le test qui traduit son critère d'acceptation (il échoue).
3. Écrire le minimum de code pour le faire passer.
4. `python -m pytest` vert, puis relire le diff : rien de hors story.
5. Mettre à jour la doc touchée (`docs/architecture.md`, README si un statut change) et cocher la case du backlog.
6. Commit petit et ciblé, message à l'impératif en anglais (`Add compute_ranking_average with page-8 examples`). Une story = un ou plusieurs commits, jamais un commit fourre-tout.

## Tests
- Les outils déterministes sont testés **sans réseau, sans clé, sans API**. Les exemples officiels sont écrits en dur (les deux exemples de la page 8 pour `compute_ranking_average`).
- Le code qui appelle le modèle passe par `src/clients/` ; ses tests utilisent un faux client. `pytest` et la CI n'appellent jamais l'API Meta.
- Les évaluations (`evals/`) consomment des crédits : lancement manuel uniquement, résultats bruts commités dans `evals/results/`.
- Tout bogue corrigé reçoit un test de non-régression.
- Lancer les tests avec `python -m pytest` (pas `pytest` seul : le paquet `src` n'est pas dans le chemin).

## Modèle et API
- `muse-spark-1.3` raisonne avant de répondre, et ces tokens comptent dans `max_tokens` : prévoir une limite large (mesuré : 228 tokens de raisonnement pour un mot). Un contenu vide avec `finish_reason = length` signale une limite trop basse.
- Les paramètres du modèle (nom, `max_tokens`, `base_url`) vivent dans `src/clients/`, pas dispersés.
- Le comportement d'un modèle non testé n'est jamais écrit comme acquis dans la doc.

## Secrets et sécurité
- `MUSE_API_KEY` uniquement dans `.env` (ignoré par git), lue côté serveur. Jamais dans le code, les logs, les messages d'erreur, les fichiers servis par le web.
- Ne jamais committer : `.env`, `env`, le PDF du guide (`data/source/`), des données réelles. Vérifier `git status` avant `git add` ; ajouter les fichiers par nom, pas `git add .`.
- Entrées de la démo (photo, audio, texte) : taille et type limités côté serveur ; le contenu envoyé au modèle est traité comme donnée, jamais comme instruction.

## Données
- `data/` est une source : le code la lit, ne la modifie pas. Une correction passe par un script ou par une ligne tracée dans `docs/data-audit.md`.
- Chaque fait affiché est traçable : `Offre_ID` + page du PDF (`data/pages_offres.csv`).

## Git
- `main` reste toujours exécutable. Tests locaux verts avant tout push.
- **À partir du 2 novembre (J7)** : aucun push sur `main` sans `python -m pytest` vert en local, et aucun nouveau déploiement après le gel du 3 novembre au soir (un déploiement automatique cassé la veille de la soumission est le pire scénario).
- Pas de `--force` sur `main`.
- **Aucune mention d'agent IA** dans les commits et les PR : pas de ligne `Co-authored-by` d'un assistant (Claude, Cursor, Copilot, Codex...), pas de « Generated with ... », pas de lien de session. L'auteur d'un commit est la personne qui le pousse.

## Définition de « terminé » (une story)
- [ ] Critère d'acceptation du backlog vérifié, pas seulement « ça marche chez moi »
- [ ] Test écrit, `python -m pytest` vert
- [ ] Aucune clé, aucun chemin personnel, aucune donnée réelle dans le diff
- [ ] Doc mise à jour (statuts dans README et `docs/architecture.md` exacts)
- [ ] Case cochée dans `docs/backlog.md`

## Commandes
```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt   # une fois
.venv/bin/python -m pytest                                           # tests
.venv/bin/uvicorn src.api.server:app --reload --port 8000            # démo locale
```
