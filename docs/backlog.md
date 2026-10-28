# Backlog PathProof

Découpage de `docs/prd.md` (version du 27 oct) en epics et stories. Le calendrier du PRD (section 11) fait office de plan de sprint : il n'y en a pas d'autre. Cocher une case seulement quand le critère d'acceptation est vérifié.

**Tailles :** S ≤ 2 h, M ≈ demi-journée, L ≈ journée. **Jours :** J1 = mar 27 oct, J2 = mer 28, J3 = jeu 29, J4 = ven 30, J5 = sam 31, J6 = dim 1er nov, J7 = lun 2, J8 = mar 3 (gel au soir), J9 = mer 4 (marge ; limite 21 h ET = 03 h à Porto-Novo).

**Suivi :** une issue GitHub par story (liens `#N` ci-dessous), regroupées en 8 milestones J1 à J8 ; labels `epic:*`, `type:*`, `size:*`, `critical-path`, `needs-human`, `conditional`, `cut-line`. Les critères des issues sont la version stricte des critères d'acceptation de ce fichier. **Règles de code :** voir `AGENTS.md` (nommage, structure, tests, définition de « terminé »). **Règles :** hors périmètre = pas de RIASEC, TTS, WhatsApp, calcul de bourse (voir PRD section 8) ; toute idée nouvelle va dans `docs/decisions.md`. Aucun chiffre d'impact sans source officielle.

## Graphe de dépendances

```
E0 spikes (vision / voix / SAM / aller-retour multi-outils) ──► décisions (zoom_cell go/no-go, endpoints)
data/ ─► E1.1 normalisation matières ─► E1.2 compute_ranking_average ─────┐
                          └► E3.1 parseur Matières ─► E3.5 lookup_filieres ┤
E0.4 vision ─► E1.3 read_grade_sheet ──────────────────────────────────────┤
E0.5 voix ─► E2.1 transcribe_voice ─► E2.2 extract_profile ───────────────┤
E1.4 format des preuves ─► E2.4 verify_report ────────────────────────────┤
                                                                          ▼
                  E4 boucle 12 pas + ask_student ─► build_report ─► CLI bout en bout (O1)
                                                                          ▼
                  E5 /run en flux + UI + mode dégradé + déploiement ─► E6 évals ─► E7 soumission
```

**Chemin critique :** format des preuves → `verify_report` → boucle → CLI → web → évals. `zoom_cell` est abandonné (NO GO, E0.6).

**Tranche verticale (E2.5, fin J3) :** une exécution sans vision ni voix (notes et profil saisis en JSON) traverse calcul → recherche → brouillon → vérificateur. Le J5 ajoute ensuite la vision et la voix, il ne découvre pas la boucle. Écart au PRD : `verify_report` passe du J5 au J3.

---

## E0 — Fondations et spikes (J1, mar 27 oct)

- [x] **E0.1 (S)** Secrets et marque : renommer le fichier `env` en `.env` (action de l'équipe) ; remplacer OrientBot par PathProof dans `web/index.html`, `src/api/server.py`, `LICENSE` ; `MAX_STEPS = 12` dans `src/agent/loop.py`. *Fait le 27 oct.*
  *Acceptation :* `grep -ri orientbot --exclude-dir=.git --exclude-dir=.agents --exclude-dir=.claude .` ne renvoie que le README (section V1), `docs/v1-reuse.md`, `docs/prd.md` (section 14) et ce backlog ; `git check-ignore .env` répond ; `git ls-files env` est vide. *Vérifié, et un appel à `muse-spark-1.3` avec la clé de `.env` réussit.*
- [ ] **E0.2 (S)** [#4](https://github.com/AresGn/PathProof-Meta-Hackathon/issues/4) Chaque membre réclame ses 150 $ de crédits et active l'alerte de dépense (action de l'équipe).
  *Acceptation :* la page Billing affiche les crédits et l'alerte.
- [x] **E0.3 (M)** [#5](https://github.com/AresGn/PathProof-Meta-Hackathon/issues/5) Jeu d'exemples fictifs : relevé net série D (moyenne générale 11,2 ; SVT 15, Maths 12, PCT 12), relevé net série C, relevé flou, deux notes vocales (une cohérente avec le relevé D, « peut-être médecin » ; une contradictoire, « 14 de moyenne »).
  *Acceptation :* 5 fichiers dans `data/samples/`, `data/samples/README.md` à jour, aucune donnée réelle.
- [x] **E0.4 (S)** [#6](https://github.com/AresGn/PathProof-Meta-Hackathon/issues/6) Spike vision : relevé D → JSON, trois exécutions.
  *Acceptation :* les 3 JSON sont identiques (`diff`) ; résultat noté dans `docs/decisions.md`. *Dép. :* E0.3.
- [x] **E0.5 (S)** [#7](https://github.com/AresGn/PathProof-Meta-Hackathon/issues/7) Spike voix : identifiant du modèle et format audio relevés dans la documentation officielle ; transcription française de la note vocale.
  *Acceptation :* URL de la doc citée ; texte transcrit ; présence ou non d'un score de confiance notée. *Dép. :* E0.3.
- [x] **E0.6 (S)** [#8](https://github.com/AresGn/PathProof-Meta-Hackathon/issues/8) Spike SAM 3.1 : localiser une cellule de tableau avec un prompt texte.
  *Acceptation :* décision **go / no go** pour `zoom_cell` écrite dans `docs/decisions.md`. *Dép. :* E0.3. *Résultat :* **NO GO** (0 essai sur 3, net et flou).
- [x] **E0.7 (M)** [#9](https://github.com/AresGn/PathProof-Meta-Hackathon/issues/9) Spike aller-retour : deux outils, le modèle choisit, le résultat lui est renvoyé, sa réponse finale l'utilise (extension de `scripts/test_muse_tool_call.py`).
  *Acceptation :* 5 exécutions sur 5 dont la réponse finale contient la valeur renvoyée par l'outil ; rapport commité dans `docs/`.
- [x] **E0.8 (S)** [#46](https://github.com/AresGn/PathProof-Meta-Hackathon/issues/46) Expérience image : tester la génération d'image de Meta sur un rapport pour les parents. *Expérience hors chemin critique, à couper en premier si le retard s'installe.* Script jetable qui envoie à l'API de génération d'image (doc officielle `dev.meta.ai/docs/image-generation`) le contenu du relevé D (moyenne 11,2 ; moyenne de classement Médecine 13,15 ; 3 filières ; bourses) et demande une carte récapitulative pour les parents, 3 exécutions. Contrôle manuel de chaque image : chiffres, noms de filières, accents, orthographe. Comparaison avec un rendu par code (HTML vers PNG) à partir des mêmes données.
  *Acceptation :* modèle, format et taille relevés dans la doc officielle (URL citée) ; 3 images brutes dans `docs/spikes/image/` ; tableau des erreurs par exécution (chiffre faux, nom déformé, texte illisible) et coût en crédits dans `docs/decisions.md`. L'image générée n'est jamais présentée comme un rapport vérifié (elle ne passe pas par `verify_report`). Le README et la vidéo ne décrivent que le résultat mesuré, y compris s'il est mauvais. *Dép. :* E0.3. *Ne bloque rien.*

## E1 — Cœur déterministe et lecture de relevé (J2, mer 28 oct)

- [x] **E1.1 (S)** [#10](https://github.com/AresGn/PathProof-Meta-Hackathon/issues/10) Chargeur de coefficients et normalisation des matières (casse, accents, « PCT » et « SPCT », « Maths ») pour C et D, à partir de `data/coefficients_bac_benin.json`.
  *Acceptation :* tests : chaque alias retenu se résout ; une matière inconnue lève une erreur explicite.
- [x] **E1.2 (M)** [#11](https://github.com/AresGn/PathProof-Meta-Hackathon/issues/11) `compute_ranking_average` : `M = Σ(mi·ci) / Σci`, avec détail et provenance de chaque coefficient. *Dép. :* E1.1.
  *Acceptation :* **les deux exemples de la page 8 écrits en dur dans les tests** (Médecine D : SVT 5, Maths 4, PCT 4 ; Médecine C : SVT 2, Maths 6, PCT 5 ; sur 13) ; SVT 15, Maths 12, PCT 12 en série D → 13,15 (2 décimales, demi vers le haut) ; coefficient manquant → « non calculé » avec la raison.
- [x] **E1.3 (M)** [#12](https://github.com/AresGn/PathProof-Meta-Hackathon/issues/12) `read_grade_sheet` : JSON strict `[{matiere, note, lisible}]`, `null` si illisible. *Dép. :* E0.3, E0.4, E1.1.
  *Acceptation :* sortie validée par schéma sur 2 relevés fictifs ; note hors 0–20 ou matière invalide pour la série signalée (FR-3), jamais de valeur par défaut.
- [ ] **E1.4 (S)** [#13](https://github.com/AresGn/PathProof-Meta-Hackathon/issues/13) Format des preuves figé (`grade`, `transcript`, `filiere`, `calc`), documenté dans `docs/architecture.md`.
  *Acceptation :* schéma versionné ; 4 exemples valides et 4 invalides en tests.

- [ ] **E1.5 (S)** [#14](https://github.com/AresGn/PathProof-Meta-Hackathon/issues/14) CI minimale : workflow GitHub Actions `.github/workflows/tests.yml` + badge dans le README. *Dép. :* E1.2 (pour qu'un test significatif tourne).
  *Acceptation :* le workflow est vert sur `main` ; le badge du README s'affiche ; le workflow n'utilise aucun secret et n'appelle pas l'API (les 10 évaluations ne tournent jamais en CI).

> **Checkpoint A (fin J2) :** `python -m pytest` vert, dont les deux exemples de la page 8, **et le workflow vert sur GitHub** ; `read_grade_sheet` fonctionne sur 2 relevés ; décision `zoom_cell` prise.

## E2 — Voix, profil, questions, vérificateur (J3, jeu 29 oct)

- [ ] **E2.1 (M)** [#15](https://github.com/AresGn/PathProof-Meta-Hackathon/issues/15) `transcribe_voice`. *Dép. :* E0.5.
  *Acceptation :* texte obtenu pour l'échantillon français ; échec réseau → erreur typée, jamais de texte inventé.
- [ ] **E2.2 (M)** [#16](https://github.com/AresGn/PathProof-Meta-Hackathon/issues/16) `extract_profile` : série, moyenne déclarée, intérêts, métier visé, contraintes, chacun avec sa citation exacte. *Dép. :* E2.1.
  *Acceptation :* test : chaque citation est une sous-chaîne exacte de la transcription ; champ absent → `null`.
- [ ] **E2.3 (S)** [#17](https://github.com/AresGn/PathProof-Meta-Hackathon/issues/17) `ask_student` : suspend la boucle et reprend avec la réponse.
  *Acceptation :* test : la boucle renvoie une question puis reprend à la réponse ; sans réponse, aucun appel d'outil suivant.
- [ ] **E2.4 (M)** [#18](https://github.com/AresGn/PathProof-Meta-Hackathon/issues/18) `verify_report` : contrôle que chaque preuve existe et correspond. *Dép. :* E1.4.
  *Acceptation :* 4 tests de falsification (une note modifiée, une citation inventée, un `Offre_ID` absent, un calcul faux) échouent tous ; un rapport correct renvoie une liste vide ; échec fermé (un rapport `None`, sans `claims`, ou une exception bloque le rapport) ; le message de refus donne `type` et `claim_id`, jamais la valeur attendue.
- [ ] **E2.5 (M)** [#19](https://github.com/AresGn/PathProof-Meta-Hackathon/issues/19) **Tranche verticale** sans vision ni voix : entrée JSON → `compute_ranking_average` → recherche provisoire → brouillon avec preuves → `verify_report`. *Dép. :* E1.2, E2.4.
  *Acceptation :* une exécution scriptée imprime un rapport vérifié pour la série D.

> **Checkpoint B (fin J3) :** la tranche verticale tourne. Sinon, on ne commence pas E3.

## E3 — Données et recherche (J4, ven 30 oct)

- [ ] **E3.1 (M)** [#20](https://github.com/AresGn/PathProof-Meta-Hackathon/issues/20) Découpage de la colonne `Matières` par série. *Dép. :* E1.1.
  *Acceptation :* 222 offres sur 224 ; `PUB-062` → Maths, PCT, SVT ; `PUB-077` corrigé ; `PUB-220` et `PUB-223` = « matières non publiées » ; couverture des offres `OK` en mode Classement reproduite : C 146 sur 149, D 147 sur 150.
- [ ] **E3.2 (M)** [#21](https://github.com/AresGn/PathProof-Meta-Hackathon/issues/21) Terminer `data/pages_offres.csv` (19 lignes `a_verifier`, 2 `introuvable`).
  *Acceptation :* plus aucun `a_verifier` ; `PUB-064` → page 36 ; `PUB-122` et `PUB-210` résolus ou marqués « page non établie ».
- [ ] **E3.3 (M)** [#22](https://github.com/AresGn/PathProof-Meta-Hackathon/issues/22) Audit de 20 lignes `OK` tirées au hasard (graine fixée) contre le PDF local. *Dép. :* E3.2.
  *Acceptation :* `docs/data-audit.md` avec le tableau des 20 lignes et les écarts. Sans cet audit, le mot « vérifié » ne figure pas dans le README.
- [ ] **E3.4 (S)** [#23](https://github.com/AresGn/PathProof-Meta-Hackathon/issues/23) Colonne `faculte_classique`.
  *Acceptation :* règle « le nom commence par Faculté » appliquée, puis relue à la main.
- [ ] **E3.5 (L)** [#24](https://github.com/AresGn/PathProof-Meta-Hackathon/issues/24) `lookup_filieres` réécrit : accès strict (ligne `OK`, série dans `Bac_recommandé`, mode d'entrée affiché), classement par mots entiers, lignes exclues renvoyées avec leur statut. *Dép. :* E3.1, E3.2.
  *Acceptation :* « pilote » ne renvoie pas Foresterie Tropicale ; `PUB-064` figure dans les lignes non vérifiées ; une offre Concours porte « les notes du Bac ne suffisent pas » ; l'ancien `tests/test_lookup_filieres.py` et `data/filieres.csv` sont remplacés/supprimés.
- [ ] ~~**E3.6 (M)** [#25](https://github.com/AresGn/PathProof-Meta-Hackathon/issues/25) `zoom_cell` — **seulement si E0.6 = go**. *Dép. :* E0.6.~~ **Abandonné : E0.6 = NO GO** (`docs/decisions.md`). Issue fermée « won't do ».
  ~~*Acceptation :* une cellule floue est relue, ou renvoyée `null`.~~

> **Checkpoint C (fin J4) :** audit publié ; `lookup_filieres` testé sur les cas `false_friend`, `unverified_trap` et `concours_entry`.

## E4 — Boucle complète en ligne de commande (J5, sam 31 oct)

- [ ] **E4.1 (L)** [#26](https://github.com/AresGn/PathProof-Meta-Hackathon/issues/26) Schémas des outils et boucle réécrite (12 pas, journal des étapes réutilisable par le web). *Dép. :* E2.3, E3.5.
  *Acceptation :* test avec un faux modèle : arrêt exact au pas 12 ; `ask_student` suspend la boucle ; une erreur d'outil devient une observation, sans plantage ; après 3 refus consécutifs de `verify_report`, arrêt avec le statut `unverified` (au 3e refus, pas au 12e pas).
- [ ] **E4.2 (M)** [#27](https://github.com/AresGn/PathProof-Meta-Hackathon/issues/27) `build_report` : accessibilité, correspondance, quotas du guide, moyenne de classement, 3 choix pour apresmonbac.bj, « Ce que je n'ai pas pu vérifier ». *Dép. :* E2.4.
  *Acceptation :* refuse de produire un rapport si `verify_report` renvoie un problème ; aucune phrase d'admission ni de ville (test sur le texte produit) ; en statut `unverified`, les affirmations refusées vont sous « Ce que je n'ai pas pu vérifier », jamais présentées comme des faits.
- [ ] **E4.3 (S)** [#28](https://github.com/AresGn/PathProof-Meta-Hackathon/issues/28) Prompt système : décider, demander, ne pas calculer, ne pas inventer. *Dép. :* E4.1.
  *Acceptation :* relu contre la section 0 du PRD.
- [ ] **E4.4 (L)** [#29](https://github.com/AresGn/PathProof-Meta-Hackathon/issues/29) Exécution en ligne de commande de `clear_sheet_d_medecin` (relevé + audio → rapport). *Dép. :* E4.1, E4.2, E4.3, E1.3, E2.2.
  *Acceptation (O1) :* sans intervention, rapport vérifié contenant `PUB-062` et `PUB-133`, avec au moins 4 appels d'outils.

> **Checkpoint D (fin J5) :** O1 atteint. Si E4.4 échoue, le J6 sert à le réparer, pas à faire le web.

## E5 — Démo web (J6, dim 1er nov)

- [ ] **E5.1 (M)** [#30](https://github.com/AresGn/PathProof-Meta-Hackathon/issues/30) `POST /run` en flux d'événements (outil, entrée, sortie, décision) à la place du 501 de `src/api/server.py`. *Dép. :* E4.1.
  *Acceptation :* test : les événements arrivent dans l'ordre ; une question produit l'état `needs_input`.
- [ ] **E5.2 (L)** [#31](https://github.com/AresGn/PathProof-Meta-Hackathon/issues/31) Interface : envoi photo + audio, trace en direct, questions de l'agent, preuves cliquables, exemples fictifs proposés aux juges. *Dép. :* E5.1.
  *Acceptation :* un juge lance un cas sans rien préparer ; chaque preuve ouvre sa source.
- [ ] **E5.3 (M)** [#32](https://github.com/AresGn/PathProof-Meta-Hackathon/issues/32) Mode dégradé : la dernière exécution réussie est rejouée avec la mention « exécution enregistrée » (FR-11). *Dép. :* E5.1.
  *Acceptation :* réseau coupé, la page affiche l'enregistrement et la mention.
- [ ] **E5.4 (M)** [#33](https://github.com/AresGn/PathProof-Meta-Hackathon/issues/33) Déploiement public, limite d'usage, clé côté serveur. *Dép. :* E5.2.
  *Acceptation :* URL publique sur Vercel, redéployée à chaque push sur `main` ; la clé n'apparaît dans aucun fichier servi (`curl` puis `grep`) ; le quota par IP est testé. À partir du J7, aucun push sur `main` sans tests locaux verts.

## E6 — Évaluation (J7, lun 2 nov)

- [ ] **E6.1 (M)** [#34](https://github.com/AresGn/PathProof-Meta-Hackathon/issues/34) Fichiers d'exemple des 10 cas de `evals/cases.jsonl`. *Dép. :* E0.3.
  *Acceptation :* plus aucune ligne « sample file TODO » ; les assertions des cas ne sont jamais chargées dans le prompt, les outils ou le contexte de l'agent (aucun module de `src/` ne lit `evals/`).
- [ ] **E6.2 (M)** [#35](https://github.com/AresGn/PathProof-Meta-Hackathon/issues/35) Lanceur d'évaluation. *Dép. :* E4.4.
  *Acceptation :* `evals/results/` contient une sortie brute par cas et un tableau (conformité, appels d'outils, questions posées, durée). *Facultatif :* `verify_report` rejouable sur un résultat enregistré, sans relancer l'agent.
- [ ] **E6.3 (L)** [#36](https://github.com/AresGn/PathProof-Meta-Hackathon/issues/36) Corrections jusqu'à 9 cas sur 10 conformes et 0 affirmation sans preuve. *Dép. :* E6.2.
  *Acceptation (O2 à O5) :* tableau commité, échecs expliqués.
- [ ] **E6.4 (S)** [#37](https://github.com/AresGn/PathProof-Meta-Hackathon/issues/37) Démo testée depuis un autre appareil ; équipe inscrite sur la plateforme CV. *Dép. :* E5.4.
  *Acceptation (O6) :* journal daté dans `docs/decisions.md`.

> **Checkpoint E (fin J7) :** O1 à O6 mesurés. Sinon, on réduit le périmètre, on n'ajoute rien.

## E7 — Soumission (J8, mar 3 nov, gel au soir ; J9 marge)

- [ ] **E7.1 (M)** [#38](https://github.com/AresGn/PathProof-Meta-Hackathon/issues/38) README final : statut réel, section V1, modèles réellement utilisés, limites, équipe ; `docs/impact.md` avec le chiffre officiel sourcé. *Dép. :* E6.3.
  *Acceptation :* aucun `TODO` dans le README ; chaque affirmation correspond à un résultat commité.
- [ ] **E7.2 (L)** [#39](https://github.com/AresGn/PathProof-Meta-Hackathon/issues/39) Vidéo de 3 minutes, sous-titres anglais, moment fort d'abord (`docs/demo-script.md`). *Dép. :* E6.3.
  *Acceptation :* durée ≤ 3:00 ; chaque plan montre une exécution réelle.
- [ ] **E7.3 (S)** [#40](https://github.com/AresGn/PathProof-Meta-Hackathon/issues/40) Post X avec la vidéo. *Dép. :* E7.2.
  *Acceptation :* lien noté pour la soumission.
- [ ] **E7.4 (S)** [#41](https://github.com/AresGn/PathProof-Meta-Hackathon/issues/41) Contrôle avant soumission : recherche de secrets dans l'arbre et l'historique, dépôt ouvert sans connexion, aucun chemin personnel. *Dép. :* E7.1.
  *Acceptation :* checklist de la section 15 du PRD entièrement cochée.
- [ ] **E7.5 (S)** [#42](https://github.com/AresGn/PathProof-Meta-Hackathon/issues/42) Soumission sur la plateforme CV. *Dép. :* tout.
  *Acceptation :* accusé de réception archivé. **Visée : le 3 nov au soir** ; limite : 4 nov, 21 h ET = 03 h à Porto-Novo.

---

## Coupes si le retard s'installe (dans l'ordre)
1. Post X et prix Viral (E7.3).
2. Cas d'évaluation réduits à 7, en gardant `voice_contradicts_sheet`, `unverified_trap` et `false_friend`.

**Ne se coupe pas :** l'audit des 20 lignes (sinon retirer le mot « vérifié »), `verify_report`, le mode dégradé.

## Points de vigilance
- **J4 et J5 sont chargés.** E3.5 et E4.1 sont les deux stories L les plus risquées ; le checkpoint B protège le J5.
- **`muse-spark-1.3` raisonne avant de répondre, et ces tokens comptent dans `max_tokens`.** Mesuré le 27 oct : une réponse d'un mot (« ok ») a consommé 228 tokens de raisonnement ; avec `max_tokens=20`, le contenu revient vide (`finish_reason = length`). Prévoir une limite large dans la boucle et les outils, et suivre la dépense réelle (budget de 150 $).
- Environnement : `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt` (`.venv/` est ignoré par git).
- `pytest` seul échoue à la collecte (le paquet `src` n'est pas dans le chemin) : utiliser `python -m pytest`.
