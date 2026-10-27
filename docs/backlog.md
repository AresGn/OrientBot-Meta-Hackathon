# Backlog PathProof

Découpage de `docs/prd.md` (version du 27 oct) en epics et stories. Le calendrier du PRD (section 11) fait office de plan de sprint : il n'y en a pas d'autre. Cocher une case seulement quand le critère d'acceptation est vérifié.

**Tailles :** S ≤ 2 h, M ≈ demi-journée, L ≈ journée. **Jours :** J1 = mar 27 oct, J2 = mer 28, J3 = jeu 29, J4 = ven 30, J5 = sam 31, J6 = dim 1er nov, J7 = lun 2, J8 = mar 3 (gel au soir), J9 = mer 4 (marge ; limite 21 h ET = 03 h à Porto-Novo).

**Règles :** hors périmètre = pas de RIASEC, TTS, WhatsApp, calcul de bourse (voir PRD section 8) ; toute idée nouvelle va dans `docs/decisions.md`. Aucun chiffre d'impact sans source officielle.

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

**Chemin critique :** format des preuves → `verify_report` → boucle → CLI → web → évals. `zoom_cell` est hors chemin critique.

**Tranche verticale (E2.5, fin J3) :** une exécution sans vision ni voix (notes et profil saisis en JSON) traverse calcul → recherche → brouillon → vérificateur. Le J5 ajoute ensuite la vision et la voix, il ne découvre pas la boucle. Écart au PRD : `verify_report` passe du J5 au J3.

---

## E0 — Fondations et spikes (J1, mar 27 oct)

- [ ] **E0.1 (S)** Secrets et marque : renommer le fichier `env` en `.env` (action de l'équipe) ; remplacer OrientBot par PathProof dans `web/index.html`, `src/api/server.py`, `LICENSE` ; `MAX_STEPS = 12` dans `src/agent/loop.py`.
  *Acceptation :* `grep -ri orientbot --exclude-dir=.git --exclude-dir=.agents --exclude-dir=.claude .` ne renvoie que le README (section V1) et `docs/v1-reuse.md` ; `git check-ignore .env` répond ; `git ls-files env` est vide.
- [ ] **E0.2 (S)** Chaque membre réclame ses 150 $ de crédits et active l'alerte de dépense (action de l'équipe).
  *Acceptation :* la page Billing affiche les crédits et l'alerte.
- [ ] **E0.3 (M)** Jeu d'exemples fictifs : relevé net série D (moyenne générale 11,2 ; SVT 15, Maths 12, PCT 12), relevé net série C, relevé flou, note vocale « 14 de moyenne ».
  *Acceptation :* 4 fichiers dans `data/samples/`, `data/samples/README.md` à jour, aucune donnée réelle.
- [ ] **E0.4 (S)** Spike vision : relevé D → JSON, trois exécutions.
  *Acceptation :* les 3 JSON sont identiques (`diff`) ; résultat noté dans `docs/decisions.md`. *Dép. :* E0.3.
- [ ] **E0.5 (S)** Spike voix : identifiant du modèle et format audio relevés dans la documentation officielle ; transcription française de la note vocale.
  *Acceptation :* URL de la doc citée ; texte transcrit ; présence ou non d'un score de confiance notée. *Dép. :* E0.3.
- [ ] **E0.6 (S)** Spike SAM 3.1 : localiser une cellule de tableau avec un prompt texte.
  *Acceptation :* décision **go / no go** pour `zoom_cell` écrite dans `docs/decisions.md`. *Dép. :* E0.3.
- [ ] **E0.7 (M)** Spike aller-retour : deux outils, le modèle choisit, le résultat lui est renvoyé, sa réponse finale l'utilise (extension de `scripts/test_muse_tool_call.py`).
  *Acceptation :* 5 exécutions sur 5 dont la réponse finale contient la valeur renvoyée par l'outil ; rapport commité dans `docs/`.

## E1 — Cœur déterministe et lecture de relevé (J2, mer 28 oct)

- [ ] **E1.1 (S)** Chargeur de coefficients et normalisation des matières (casse, accents, « PCT » et « SPCT », « Maths ») pour C et D, à partir de `data/coefficients_bac_benin.json`.
  *Acceptation :* tests : chaque alias retenu se résout ; une matière inconnue lève une erreur explicite.
- [ ] **E1.2 (M)** `compute_ranking_average` : `M = Σ(mi·ci) / Σci`, avec détail et provenance de chaque coefficient. *Dép. :* E1.1.
  *Acceptation :* **les deux exemples de la page 8 écrits en dur dans les tests** (Médecine D : SVT 5, Maths 4, PCT 4 ; Médecine C : SVT 2, Maths 6, PCT 5 ; sur 13) ; SVT 15, Maths 12, PCT 12 en série D → 13,2 ; coefficient manquant → « non calculé » avec la raison.
- [ ] **E1.3 (M)** `read_grade_sheet` : JSON strict `[{matiere, note, lisible}]`, `null` si illisible. *Dép. :* E0.3, E0.4, E1.1.
  *Acceptation :* sortie validée par schéma sur 2 relevés fictifs ; note hors 0–20 ou matière invalide pour la série signalée (FR-3), jamais de valeur par défaut.
- [ ] **E1.4 (S)** Format des preuves figé (`grade`, `transcript`, `filiere`, `calc`), documenté dans `docs/architecture.md`.
  *Acceptation :* schéma versionné ; 4 exemples valides et 4 invalides en tests.

> **Checkpoint A (fin J2) :** `python -m pytest` vert, dont les deux exemples de la page 8 ; `read_grade_sheet` fonctionne sur 2 relevés ; décision `zoom_cell` prise.

## E2 — Voix, profil, questions, vérificateur (J3, jeu 29 oct)

- [ ] **E2.1 (M)** `transcribe_voice`. *Dép. :* E0.5.
  *Acceptation :* texte obtenu pour l'échantillon français ; échec réseau → erreur typée, jamais de texte inventé.
- [ ] **E2.2 (M)** `extract_profile` : série, moyenne déclarée, intérêts, métier visé, contraintes, chacun avec sa citation exacte. *Dép. :* E2.1.
  *Acceptation :* test : chaque citation est une sous-chaîne exacte de la transcription ; champ absent → `null`.
- [ ] **E2.3 (S)** `ask_student` : suspend la boucle et reprend avec la réponse.
  *Acceptation :* test : la boucle renvoie une question puis reprend à la réponse ; sans réponse, aucun appel d'outil suivant.
- [ ] **E2.4 (M)** `verify_report` : contrôle que chaque preuve existe et correspond. *Dép. :* E1.4.
  *Acceptation :* 4 tests de falsification (une note modifiée, une citation inventée, un `Offre_ID` absent, un calcul faux) échouent tous ; un rapport correct renvoie une liste vide.
- [ ] **E2.5 (M)** **Tranche verticale** sans vision ni voix : entrée JSON → `compute_ranking_average` → recherche provisoire → brouillon avec preuves → `verify_report`. *Dép. :* E1.2, E2.4.
  *Acceptation :* une exécution scriptée imprime un rapport vérifié pour la série D.

> **Checkpoint B (fin J3) :** la tranche verticale tourne. Sinon, on ne commence pas E3.

## E3 — Données et recherche (J4, ven 30 oct)

- [ ] **E3.1 (M)** Découpage de la colonne `Matières` par série. *Dép. :* E1.1.
  *Acceptation :* 222 offres sur 224 ; `PUB-062` → Maths, PCT, SVT ; `PUB-077` corrigé ; `PUB-220` et `PUB-223` = « matières non publiées » ; couverture des offres `OK` en mode Classement reproduite : C 146 sur 149, D 147 sur 150.
- [ ] **E3.2 (M)** Terminer `data/pages_offres.csv` (19 lignes `a_verifier`, 2 `introuvable`).
  *Acceptation :* plus aucun `a_verifier` ; `PUB-064` → page 36 ; `PUB-122` et `PUB-210` résolus ou marqués « page non établie ».
- [ ] **E3.3 (M)** Audit de 20 lignes `OK` tirées au hasard (graine fixée) contre le PDF local. *Dép. :* E3.2.
  *Acceptation :* `docs/data-audit.md` avec le tableau des 20 lignes et les écarts. Sans cet audit, le mot « vérifié » ne figure pas dans le README.
- [ ] **E3.4 (S)** Colonne `faculte_classique`.
  *Acceptation :* règle « le nom commence par Faculté » appliquée, puis relue à la main.
- [ ] **E3.5 (L)** `lookup_filieres` réécrit : accès strict (ligne `OK`, série dans `Bac_recommandé`, mode d'entrée affiché), classement par mots entiers, lignes exclues renvoyées avec leur statut. *Dép. :* E3.1, E3.2.
  *Acceptation :* « pilote » ne renvoie pas Foresterie Tropicale ; `PUB-064` figure dans les lignes non vérifiées ; une offre Concours porte « les notes du Bac ne suffisent pas » ; l'ancien `tests/test_lookup_filieres.py` et `data/filieres.csv` sont remplacés/supprimés.
- [ ] **E3.6 (M)** `zoom_cell` — **seulement si E0.6 = go**. *Dép. :* E0.6.
  *Acceptation :* une cellule floue est relue, ou renvoyée `null`.

> **Checkpoint C (fin J4) :** audit publié ; `lookup_filieres` testé sur les cas `false_friend`, `unverified_trap` et `concours_entry`.

## E4 — Boucle complète en ligne de commande (J5, sam 31 oct)

- [ ] **E4.1 (L)** Schémas des outils et boucle réécrite (12 pas, journal des étapes réutilisable par le web). *Dép. :* E2.3, E3.5.
  *Acceptation :* test avec un faux modèle : arrêt exact au pas 12 ; `ask_student` suspend la boucle ; une erreur d'outil devient une observation, sans plantage.
- [ ] **E4.2 (M)** `build_report` : accessibilité, correspondance, quotas du guide, moyenne de classement, 3 choix pour apresmonbac.bj, « Ce que je n'ai pas pu vérifier ». *Dép. :* E2.4.
  *Acceptation :* refuse de produire un rapport si `verify_report` renvoie un problème ; aucune phrase d'admission ni de ville (test sur le texte produit).
- [ ] **E4.3 (S)** Prompt système : décider, demander, ne pas calculer, ne pas inventer. *Dép. :* E4.1.
  *Acceptation :* relu contre la section 0 du PRD.
- [ ] **E4.4 (L)** Exécution en ligne de commande de `clear_sheet_d_medecin` (relevé + audio → rapport). *Dép. :* E4.1, E4.2, E4.3, E1.3, E2.2.
  *Acceptation (O1) :* sans intervention, rapport vérifié contenant `PUB-062` et `PUB-133`, avec au moins 4 appels d'outils.

> **Checkpoint D (fin J5) :** O1 atteint. Si E4.4 échoue, le J6 sert à le réparer, pas à faire le web.

## E5 — Démo web (J6, dim 1er nov)

- [ ] **E5.1 (M)** `POST /run` en flux d'événements (outil, entrée, sortie, décision) à la place du 501 de `src/api/server.py`. *Dép. :* E4.1.
  *Acceptation :* test : les événements arrivent dans l'ordre ; une question produit l'état `needs_input`.
- [ ] **E5.2 (L)** Interface : envoi photo + audio, trace en direct, questions de l'agent, preuves cliquables, exemples fictifs proposés aux juges. *Dép. :* E5.1.
  *Acceptation :* un juge lance un cas sans rien préparer ; chaque preuve ouvre sa source.
- [ ] **E5.3 (M)** Mode dégradé : la dernière exécution réussie est rejouée avec la mention « exécution enregistrée » (FR-11). *Dép. :* E5.1.
  *Acceptation :* réseau coupé, la page affiche l'enregistrement et la mention.
- [ ] **E5.4 (M)** Déploiement public, limite d'usage, clé côté serveur. *Dép. :* E5.2.
  *Acceptation :* URL publique ; la clé n'apparaît dans aucun fichier servi (`curl` puis `grep`) ; le quota par IP est testé.

## E6 — Évaluation (J7, lun 2 nov)

- [ ] **E6.1 (M)** Fichiers d'exemple des 10 cas de `evals/cases.jsonl`. *Dép. :* E0.3.
  *Acceptation :* plus aucune ligne « sample file TODO ».
- [ ] **E6.2 (M)** Lanceur d'évaluation. *Dép. :* E4.4.
  *Acceptation :* `evals/results/` contient une sortie brute par cas et un tableau (conformité, appels d'outils, questions posées, durée).
- [ ] **E6.3 (L)** Corrections jusqu'à 9 cas sur 10 conformes et 0 affirmation sans preuve. *Dép. :* E6.2.
  *Acceptation (O2 à O5) :* tableau commité, échecs expliqués.
- [ ] **E6.4 (S)** Démo testée depuis un autre appareil ; équipe inscrite sur la plateforme CV. *Dép. :* E5.4.
  *Acceptation (O6) :* journal daté dans `docs/decisions.md`.

> **Checkpoint E (fin J7) :** O1 à O6 mesurés. Sinon, on réduit le périmètre, on n'ajoute rien.

## E7 — Soumission (J8, mar 3 nov, gel au soir ; J9 marge)

- [ ] **E7.1 (M)** README final : statut réel, section V1, modèles réellement utilisés, limites, équipe ; `docs/impact.md` avec le chiffre officiel sourcé. *Dép. :* E6.3.
  *Acceptation :* aucun `TODO` dans le README ; chaque affirmation correspond à un résultat commité.
- [ ] **E7.2 (L)** Vidéo de 3 minutes, sous-titres anglais, moment fort d'abord (`docs/demo-script.md`). *Dép. :* E6.3.
  *Acceptation :* durée ≤ 3:00 ; chaque plan montre une exécution réelle.
- [ ] **E7.3 (S)** Post X avec la vidéo. *Dép. :* E7.2.
  *Acceptation :* lien noté pour la soumission.
- [ ] **E7.4 (S)** Contrôle avant soumission : recherche de secrets dans l'arbre et l'historique, dépôt ouvert sans connexion, aucun chemin personnel. *Dép. :* E7.1.
  *Acceptation :* checklist de la section 15 du PRD entièrement cochée.
- [ ] **E7.5 (S)** Soumission sur la plateforme CV. *Dép. :* tout.
  *Acceptation :* accusé de réception archivé. **Visée : le 3 nov au soir** ; limite : 4 nov, 21 h ET = 03 h à Porto-Novo.

---

## Coupes si le retard s'installe (dans l'ordre)
1. `zoom_cell` (E3.6), déjà conditionnel.
2. Post X et prix Viral (E7.3).
3. Cas d'évaluation réduits à 7, en gardant `voice_contradicts_sheet`, `unverified_trap` et `false_friend`.

**Ne se coupe pas :** l'audit des 20 lignes (sinon retirer le mot « vérifié »), `verify_report`, le mode dégradé.

## Points de vigilance
- **J4 et J5 sont chargés.** E3.5 et E4.1 sont les deux stories L les plus risquées ; le checkpoint B protège le J5.
- `pytest` seul échoue à la collecte (le paquet `src` n'est pas dans le chemin) : utiliser `python -m pytest`.
