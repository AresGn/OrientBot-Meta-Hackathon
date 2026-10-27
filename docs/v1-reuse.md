# Ce qu'on reprend de la V1 d'OrientBot (et ce qu'on laisse)

**Règle :** on reprend des **règles métier** (spécifications) et on les réécrit dans ce dépôt pendant l'événement. Aucun fichier de code, aucune fonction ni aucun bloc de code de `orientbotv2` n'est copié. C'est ce que dit le README (« No code from it is reused here ») et ce qu'exige le cadre « new work only ». Voir aussi `docs/prd.md` (sections 0, 12 et 14).

Ce document ne cite que des éléments vérifiés dans le code de la V1 (lecture seule, dépôt privé, non lié ici). Les chemins mentionnés servent de référence interne à l'équipe ; aucun contenu de ces fichiers n'est reproduit.

---

## 1. À reprendre comme règle (réécrire from scratch)

### 1.1 Moyenne de classement par filière
- **Source dans la V1 :** `packages/domain/src/mesrs/coefficients-bac-series.ts`, calcul dans `calculer-moyenne.ts`.
- **Règle :** moyenne pondérée par les coefficients de la série du Bac. Seules les épreuves du **groupe 1 (écrit + pratique)** comptent.
- **Ce qui change par rapport à la V1 :** PathProof calcule la moyenne de **classement propre à chaque offre** : `M = (m1·x + m2·y + m3·z) / (x + y + z)`, sur les trois matières de la colonne `Matières` de l'offre, avec les coefficients de la série (guide 2026-2027, page 8). Outil : `compute_ranking_average`.
- **Source officielle :** arrêté N°016-2003/MESRS/MEPS/METFP (modifié) pour les coefficients ; *Guide d'information 2026-2027*, page 8, pour la formule.
- **Données :** `data/coefficients_bac_benin.json`. Fichier de données, pas de code. Les coefficients C et D doivent redonner les deux exemples de la page 8 (Médecine D : 5, 4, 4 ; Médecine C : 2, 6, 5), test unitaire obligatoire. L'équipe confirme que les coefficients sont ceux en vigueur au 27 octobre 2026.

### 1.2 Rapprochement des noms de matières
- **Source :** `packages/domain/src/mesrs/matcher-matieres.ts`.
- **Règle :** normaliser les deux côtés (casse, accents, pluriels, abréviations : « math », « PCT » et « SPCT », « Anglais (LV1) », « Hist-Géo/Anglais (DT/STI) »), puis résoudre les formules composées avec les matières que l'élève possède vraiment.
- **Pourquoi :** les relevés, le guide et la table des coefficients n'écrivent pas les matières de la même façon. Sans cette étape, `read_grade_sheet` produit des matières qui ne correspondent à rien.

### 1.3 Ne rien recommander sans preuve
- **Source :** principe de conception de ce dépôt (`docs/architecture.md`), pas un fichier de la V1.
- **Règle :** seules les lignes `Statut_qualité = OK` sont recommandées ; les autres sont listées dans « Ce que je n'ai pas pu vérifier ». Chaque phrase du rapport porte une preuve (`grade`, `transcript`, `filiere` ou `calc`) contrôlée par `verify_report`.

### 1.4 Demander plutôt que deviner
- **Source :** `profilage.processor.ts`, validation des notes entre 0 et 20 et des matières valides pour la série.
- **Règle :** une note hors de 0–20 ou une matière invalide pour la série déclenche une question (`ask_student`), jamais une valeur par défaut (FR-3).

---

## 2. À ne pas reprendre pour cet événement

| Élément V1 | Pourquoi on le laisse |
|---|---|
| Bot WhatsApp (Baileys), file BullMQ, Supabase | Infrastructure lourde, hors des 9 jours |
| Paiement KKiaPay, landing, codes partenaires | Hors sujet pour la démo |
| Machine d'états de session (`ACCUEIL` → `RAPPORT_PARENTS`) | Workflow fixe, remplacé par une boucle où l'agent choisit l'outil |
| Questionnaire RIASEC | **Retiré par principe** (`docs/prd.md` section 2.2) : un profil de personnalité ne se prouve pas, et six questions à choix multiples font « chatbot ». La note vocale le remplace |
| Garde-fous de recommandation (anti-saturation, public-first, strict match, bourse, validateur) | Pipeline complet trop lourd ; on garde l'idée « rien sans preuve », réalisée par `verify_report` |
| Rapport audio parents, synthèse vocale | Pas d'API TTS chez Meta |
| Calcul de bourse (`estimer-bourse.ts`) | Hors périmètre ; le rapport affiche seulement les quotas du guide |
| Appels LLM via OpenRouter / Groq / Claude | Remplacés par les modèles Meta |

---

## 3. Données : ce qu'on peut et ne peut pas faire

**Ce qui est dans le dépôt (données, pas du code) :** les CSV extraits du *Guide d'information 2026-2027*, document public officiel du MESRS. L'extraction (MinerU) a été faite avant le hackathon ; ces fichiers étaient rangés dans le dossier de la V1 (`GUIDE_2026-2027-CSV-EXCEL/`) et ont été copiés tels quels dans `data/`. Les voici :

- `offres_publiques_2026_2027.csv`, `series_et_offres_2026_2027.csv`, `controle_qualite_2026_2027.csv` ;
- `pages_offres.csv` (offre → page du PDF), produit pour PathProof ;
- `coefficients_bac_benin.json` (liste des épreuves de l'Office du Bac).

**Ce qui n'est pas dans le dépôt :**
- **Le PDF du guide.** Il porte la mention « Vente interdite ». Une copie locale existe dans `data/source/` (ignorée par git) pour vérifier les pages. On ne le republie pas tant qu'une URL officielle publique n'est pas trouvée et citée (`TODO`, voir `docs/prd.md` section 6).
- **`offres_privees_2026_2027.csv` (753 offres).** Elles ne servent à rien pour recommander (ni série, ni matières, ni débouchés) ; on réduit donc ce qu'on republie. Le README les mentionne.
- Les autres guides de la V1 (2024-2025, 2025-2026) et tout contenu issu des PDF ou Markdown de `orientbotv2`.

**Provenance à écrire dans le README :** voir `docs/prd.md` section 14. Si un doute sur la republication subsiste, on ne publie que le sous-ensemble utilisé (C et D).

---

## 4. Résumé pour l'équipe

- **Reprendre :** la formule officielle de moyenne (réécrite, avec test sur les exemples de la page 8), la normalisation des matières, la règle « rien sans preuve », la règle « demander plutôt que deviner ».
- **Laisser :** WhatsApp, paiement, TTS, parents, bourse, garde-fous complets, RIASEC.
- **Données :** CSV et JSON du guide dans `data/` ; PDF seulement en local.
- **Interdit :** copier du code ou des fichiers de code de `orientbotv2` dans ce dépôt.
