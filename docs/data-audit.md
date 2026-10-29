# Audit des données : 20 lignes OK contre le PDF officiel (E3.3)

## Méthode

Échantillon reproductible des lignes `Statut_qualité = OK` :

```bash
python scripts/sample_audit.py --seed 2026
```

Tirage : `random.Random(2026).sample()` sur les 206 lignes `OK` triées par
`Offre_ID` (test : `tests/test_sample_audit.py`). Chaque ligne est comparée
au PDF local (`data/source/guide_2026.pdf`, 116 pages, non commité) à la page
de `data/pages_offres.csv`, sur 8 champs : `Filière`, `Établissement`,
`Bourse`, `Aide_FPP`, `Mode_entrée`, `Bac_recommandé`, `Matières`,
`Débouchés_Métiers`.

Règle de verdict : un champ est conforme si sa valeur égale celle du guide
aux accents, à la casse, à la ponctuation et à l'ordre des matières près
(`PCT` = `SPCT`, E1.1). Un écart est une différence de fond : valeur fausse,
élément omis ou ajouté, texte collé. Seuil de l'issue #22 : 3 lignes avec
écart ou plus déclenchent une décision dans `docs/decisions.md`.

## Tableau 20 lignes × 8 champs

| Offre | Page | Champs (8) | Note |
|---|---|---|---|
| PUB-028 | 42 | 8/8 | — |
| PUB-032 | 39 | 7/8, Débouchés | 3 espaces manquantes, voir §1 |
| PUB-059 | 35 | 8/8 | `DEAT/PV` du guide en segment Matières |
| PUB-087 | 26 | 8/8 | coquille du guide recopiée telle quelle |
| PUB-115 | 24 | 8/8 | — |
| PUB-133 | 47 | 8/8 | `SPCT` normalisé en `PCT` |
| PUB-136 | 51 | 8/8 | — |
| PUB-139 | 52 | 8/8 | — |
| PUB-151 | 48 | 8/8 | — |
| PUB-153 | 49 | 8/8 | — |
| PUB-157 | 64 | 8/8 | `TF` étendu en `Technique de Froid` |
| PUB-164 | 66 | 8/8 | `ou` résolu par série, 3 matières partout |
| PUB-170 | 57 | 8/8 | `Science appliquées` → `Sciences Appliquées` |
| PUB-176 | 56 | 8/8 | `Hist` étendu en `Histoire` |
| PUB-202 | 75 | 8/8 | `ou` résolu, coquille `Fançais` corrigée |
| PUB-211 | 86 | 6/8, Bac + Matières | `DEAT`, `EA` omis, voir §2 |
| PUB-215 | 87 | 8/8 | mode `–` inféré, voir §3 |
| PUB-216 | 82 | 8/8 | — |
| PUB-217 | 89 | 8/8 | page à 3 colonnes, voir §3 |
| PUB-219 | 84 | 8/8 | `–` noté `Toutes séries` / `—` |

## Taux d'erreur

- **2 lignes sur 20 (10 %)** portent au moins un écart : `PUB-032`, `PUB-211`.
- **3 champs sur 160 (1,9 %)** : `Débouchés_Métiers` (`PUB-032`),
  `Bac_recommandé` et `Matières` (`PUB-211`).
- Sous le seuil de 3 lignes : pas de décision corrective, `data/` inchangé.
  Les deux écarts sont documentés ci-dessous pour E3.5.

## Écarts

### 1. PUB-032 : mots collés dans `Débouchés_Métiers` (page 39)

CSV : « contrôle deséquipements de laboratoires médicaux etvétérinaires,
Maintenance des équipementsélectroniques ».
PDF : « contrôle des équipements de laboratoires médicaux et vétérinaires,
Maintenance des équipements électroniques ».

Trois espaces manquantes. Sans effet sur l'affichage courant, mais un
rapprochement par mots entiers (E3.5) manquerait `équipements`,
`vétérinaires`, `électroniques` sur cette ligne. Recommandation E3.5 :
réparer les espaces dans `data/` via un script tracé ici, ou normaliser à
la lecture.

### 2. PUB-211 : `DEAT` et `EA` omis (page 86)

PDF, `Baccalauréat recommandé` : « A, B, C, D, G2, G3, DEAT, EA ».
CSV, `Bac_recommandé` : « A1, A2, B, C, D, G2, G3 » (`DEAT`, `EA` absents).
Le segment « Pour DEAT : toutes les trois (03) matières écrites » manque
aussi de `Matières`. Sans effet pour les séries C et D (présentes, matières
exactes), mais un bachelier DEAT/EA ne verrait pas cette offre.
Recommandation E3.5 : ajouter les deux séries et le segment DEAT, ou tracer
le choix de ne recommander qu'aux séries listées.

## Conventions d'extraction relevées

### 3. Cellules `–` et pages réduites : valeurs inférées, non transcrites

Quatre lignes de l'échantillon portent des valeurs que le guide ne donne
pas mot pour mot :

- `PUB-211`, `PUB-215` (UADC, pages 86–87) : quotas `–` notés `0`/`0`,
  mode `–` noté `Classement` (les matières listées sont des matières de
  classement par série). La page 87 précise en pied : « Mode d'entrée : A
  titre payant - les candidats sont invités à se rapprocher de l'UADC »
  (coût, pas mécanisme).
- `PUB-217` (Sèmè City, page 89) : la page n'a que 3 colonnes (N°,
  établissement, filière). Quotas notés `0`/`0`, mode noté `Dossier`,
  Bac noté `Toutes séries`, matières et débouchés `—`. Le mot `Dossier`
  n'apparaît nulle part dans le guide comme mode d'entrée (vérifié par
  recherche plein texte : `dossier` ne figure qu'aux pages 9 et 16, hors
  sujet).
- `PUB-219` (CAPESA, page 84) : Bac `–` noté `Toutes séries`, matières et
  débouchés `–` notés `—`.

Ces conventions sont raisonnables et ne contredisent pas le guide, mais une
preuve `filiere` qui citerait « Mode d'entrée : Dossier » renverrait
l'élève vers une page où ce mot ne figure pas. Recommandation E4.2 : pour
ces valeurs, le rapport dit « le guide ne publie pas… » plutôt que
d'affirmer.

### 4. Résolutions fidèles (conformes)

- `Matières` à options (`Anglais ou Français (E et F)`, `Electrotechnique
  ou EST (F2)`) : le bon sujet par série, 3 matières partout (`PUB-032`,
    `PUB-164`, `PUB-202`).
- Cellules fusionnées (débouchés partagés, `PUB-028`, `PUB-170`,
  `PUB-176`) : correctement attribuées à chaque ligne.
- Coquilles du guide : `géomantique` recopiée telle quelle (`PUB-087`),
  `Fançais` corrigée en `Français` (`PUB-202`).

## Suivi E3.2 : lignes en quarantaine (trace reprise)

7 lignes `OK` restent `page_non_etablie` : le PDF contredit leur
établissement (`docs/decisions.md`, 2026-10-29). Pages trouvées, à rétablir
après correction des libellés : `PUB-025` → 42, `PUB-045` → 23,
`PUB-048` → 24, `PUB-142` → 53, `PUB-186` → 57, `PUB-187` → 59,
`PUB-188` → 58. `PUB-189` (page 58) a une filière vide à renseigner.
Soupçons non vérifiés : `PUB-026` (homologue probable page 42), `PUB-049`
(homologue probable page 24). Correction et rétablissement : E3.5, qui
réécrit `lookup_filieres` et doit trancher le sort de ces lignes.

## Conclusion

Échantillon graine 2026 : 18 lignes sur 20 intégralement conformes,
2 écarts documentés (§1, §2), conventions listées (§3). Sous le seuil :
l'extraction tient, et le mot « vérifié » peut désormais être employé
pour ce qu'elle couvre. Aucune modification de `data/` dans cette story.
