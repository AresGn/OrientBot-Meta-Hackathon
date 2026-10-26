# Ce qu'on reprend de la V1 d'OrientBot (et ce qu'on laisse)

**Règle :** on reprend des **règles métier** (spécifications), on les réécrit dans ce dépôt pendant l'événement. Aucun fichier, aucune fonction ni aucun bloc de code de `orientbotv2` n'est copié. C'est ce que dit le README (« No code from it is copied here ») et ce qu'exige la piste Startup.

Ce document ne cite que des éléments vérifiés dans le code de la V1 (lecture seule, dépôt privé, non lié ici). Les chemins mentionnés servent de référence interne à l'équipe ; aucun contenu de ces fichiers n'est reproduit. Voir aussi `docs/prd.md`.

---

## 1. À reprendre comme règle (réécrire from scratch)

### 1.1 Calcul de la moyenne MESRS
- **Source dans la V1 :** `packages/domain/src/mesrs/coefficients-bac-series.ts`, calcul dans `calculer-moyenne.ts`.
- **Règle :** moyenne pondérée par les coefficients de la série. Seules les épreuves du **groupe 1 (écrit + pratique)** comptent pour le classement MESRS.
- **Source officielle citée dans le code :** arrêté N°016-2003/MESRS/MEPS/METFP ; Guide d'orientation universitaire MESRS 2024-2025, page 9.
- **Action :** recopier la table de coefficients **à la main** depuis la source officielle, pour les séries retenues (C et D pour la démo). Ajouter `source_url` dans le code. Vérifier qu'il n'y a pas de version 2026-2027 différente.

### 1.2 Rapprochement des noms de matières
- **Source :** `packages/domain/src/mesrs/matcher-matieres.ts`.
- **Règle :** normaliser les deux côtés (casse, accents, pluriels, abréviations comme « math », « PCT », « Ang »), puis résoudre les formules composées avec les matières que l'élève possède vraiment.
- **Pourquoi c'est utile :** les relevés et les tables officielles n'écrivent pas les matières de la même façon. Sans ça, `read_grade_sheet` produira des matières qui ne correspondent à rien.

### 1.3 Ne rien recommander sans donnée vérifiée
- **Source :** principe de conception de ce dépôt (`docs/architecture.md`), pas un fichier de la V1. La V1 cite ses sources dans le code (par exemple `coefficients-bac-series.ts`), et ce dépôt fait de même.
- **Règle :** `lookup_filieres` n'utilise que les lignes avec `source_status = verifie`. Les autres sont ignorées.

### 1.4 Demander plutôt que deviner
- **Source :** `profilage.processor.ts`, validation des notes entre 0 et 20 et des matières valides pour la série.
- **Règle :** une note hors de 0–20 ou une matière invalide pour la série déclenche une question, pas une valeur par défaut.

---

## 2. À ne pas reprendre pour cet événement

| Élément V1 | Pourquoi on le laisse |
|---|---|
| Bot WhatsApp (Baileys), file BullMQ, Supabase | Infrastructure lourde, hors des 9 jours |
| Paiement KKiaPay, landing, codes partenaires | Hors sujet pour la démo |
| Machine d'états de session (`ACCUEIL` → `RAPPORT_PARENTS`) | Remplacé par la boucle de l'agent |
| Questionnaire RIASEC (6 questions A/B/C) | Long à reprendre proprement ; on garde une saisie simple si besoin |
| Garde-fous de recommandation (anti-saturation, public-first, strict match, bourse, validateur) | Pipeline complet trop lourd ; on garde seulement l'idée « rien sans source » |
| Rapport audio parents, synthèse vocale | Pas d'API TTS chez Meta |
| Calcul de bourse (`estimer-bourse.ts`) | Hors périmètre de la démo |
| Appels LLM via OpenRouter / Groq / Claude | Remplacés par Muse Spark 1.3 |

---

## 3. Données : ce qu'on peut et ne peut pas faire

- **Guides 2025-2026 et 2026-2027** présents dans `orientbotv2` (PDF, Markdown, CSV) : **ne pas les copier** dans le dépôt public tant que leur republication n'est pas vérifiée.
- **Ce qu'on fait :** saisir à la main quelques lignes vérifiées, chacune avec l'URL publique officielle de la source. Un fait sourcé suffit, pas une copie du document.
- **Limite à écrire dans le README :** « 15 filières vérifiées pour les séries C et D, pour illustrer la boucle. Ce n'est pas une base nationale. »

---

## 4. Résumé pour l'équipe

- **Reprendre :** la table MESRS (à recopier et sourcer), la normalisation des matières, la règle « rien sans source », la règle « demander plutôt que deviner ».
- **Laisser :** WhatsApp, paiement, TTS, parents, bourse, garde-fous complets, RIASEC complet.
- **Interdit :** copier du code ou des fichiers de `orientbotv2` dans ce dépôt.
