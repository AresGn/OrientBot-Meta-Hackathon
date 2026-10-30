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
élément omis ou ajouté. Une valeur inférée d'une cellule « – » ou absente
(quota, mode, série) est un élément ajouté : écart. Seuil de l'issue #22 :
3 lignes avec écart ou plus déclenchent une décision dans
`docs/decisions.md`.

## Tableau 20 lignes × 8 champs

`FIL` Filière, `ÉTA` Établissement, `BOU` Bourse, `AID` Aide_FPP, `MOD`
Mode_entrée, `BAC` Bac_recommandé, `MAT` Matières, `DÉB` Débouchés_Métiers.

| Offre | Pg | FIL | ÉTA | BOU | AID | MOD | BAC | MAT | DÉB |
|---|---|---|---|---|---|---|---|---|---|
| PUB-028 | 42 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| PUB-032 | 39 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ |
| PUB-059 | 35 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| PUB-087 | 26 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| PUB-115 | 24 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| PUB-133 | 47 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| PUB-136 | 51 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| PUB-139 | 52 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| PUB-151 | 48 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| PUB-153 | 49 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| PUB-157 | 64 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| PUB-164 | 66 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| PUB-170 | 57 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| PUB-176 | 56 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| PUB-202 | 75 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| PUB-211 | 86 | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ |
| PUB-215 | 87 | ✓ | ✓ | ✗ | ✗ | ✗ | ✓ | ✓ | ✓ |
| PUB-216 | 82 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| PUB-217 | 89 | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✓ | ✓ |
| PUB-219 | 84 | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ |

Notes de lecture (conformes) : `PUB-059` (`DEAT/PV` du guide en segment
Matières), `PUB-087` (coquille `géomantique` du guide recopiée),
`PUB-133`/`PUB-157` (`SPCT`/`TF` normalisés), `PUB-164`/`PUB-202` (`ou`
résolu par série, 3 matières partout), `PUB-170`/`PUB-176` (libellés
étendus), `PUB-202` (coquille `Fançais` corrigée), cellules fusionnées
attribuées à chaque ligne (`PUB-028`, `PUB-170`, `PUB-176`), `A` étendu en
`A1, A2` (`PUB-211`, `PUB-215`).

## Taux d'erreur

- **5 lignes sur 20 (25 %)** portent au moins un écart : `PUB-032`,
  `PUB-211`, `PUB-215`, `PUB-217`, `PUB-219`.
- **14 champs sur 160 (8,8 %)**.
- Seuil franchi (5 ≥ 3) : décision dans `docs/decisions.md` — corriger
  l'extraction et restreindre, mis en œuvre en E3.5.

## Écarts

### 1. PUB-032 : mots collés dans `Débouchés_Métiers` (page 39)

CSV : « contrôle deséquipements de laboratoires médicaux etvétérinaires,
Maintenance des équipementsélectroniques ».
PDF : « contrôle des équipements de laboratoires médicaux et vétérinaires,
Maintenance des équipements électroniques ».

Trois espaces manquantes. Un rapprochement par mots entiers (E3.5)
manquerait `équipements`, `vétérinaires`, `électroniques` sur cette ligne.

### 2. PUB-211 : quotas, mode, séries et segment DEAT (page 86)

- `Bourse`/`Aide_FPP` : « – »/« – » notés `0`/`0`.
- `Mode_entrée` : « – » noté `Classement`.
- `Bac_recommandé` : « A, B, C, D, G2, G3, DEAT, EA » noté « A1, A2, B, C,
  D, G2, G3 » (`DEAT`, `EA` omis).
- `Matières` : le segment « Pour DEAT : toutes les trois (03) matières
  écrites » manque (les segments A/B, C/D, G2/G3 sont exacts).

### 3. PUB-215 : quotas et mode inférés (page 87)

`Bourse`/`Aide_FPP` : « – »/« – » notés `0`/`0`. `Mode_entrée` : « – »
noté `Classement`. Séries, matières (le sujet `EA` de la cellule partagée
appartient bien à l'autre ligne) et débouchés exacts. La page précise en
pied : « Mode d'entrée : A titre payant - les candidats sont invités à se
rapprocher de l'UADC » (coût, pas mécanisme).

### 4. PUB-217 : page à 3 colonnes, 4 valeurs inférées (page 89)

La page ne donne que N°, établissement et filière. Quotas notés `0`/`0`,
mode noté `Dossier`, Bac noté `Toutes séries`. Le mot `Dossier`
n'apparaît nulle part dans le guide comme mode d'entrée (vérifié par
recherche plein texte : `dossier` ne figure qu'aux pages 9 et 16, hors
sujet). Matières et débouchés `—` : transcription fidèle de l'absence.

### 5. PUB-219 : Bac inféré (page 84)

`Bac_recommandé` : « – » noté `Toutes séries`. Quotas (40/0), mode
(Concours), matières et débouchés (`—`) transcrits fidèlement.

### Portée au-delà de l'échantillon

15 lignes `OK` ont `0`/`0` (`PUB-085`, `PUB-086`, `PUB-096`–`PUB-099`,
`PUB-145`, `PUB-180`, `PUB-211`–`PUB-215`, `PUB-217`, `PUB-218`) : il faut
distinguer les vrais zéros des « – ». Les lignes UADC (`PUB-211` à
`PUB-215`) sont `OK` et calculables en série C/D : sans correction,
l'agent écrirait « 0 bourses prévues, page 86 », accepté par
`verify_report` (il compare au CSV), alors que la page affiche « – » —
le même cas que les 7 offres mises en quarantaine en E3.2.

## Suivi E3.2 : lignes en quarantaine (trace reprise)

7 lignes `OK` restent `page_non_etablie` : le PDF contredit leur
établissement (`docs/decisions.md`, 2026-10-29). Pages trouvées, à rétablir
après correction des libellés : `PUB-025` → 42, `PUB-045` → 23,
`PUB-048` → 24, `PUB-142` → 53, `PUB-186` → 57, `PUB-187` → 59,
`PUB-188` → 58. `PUB-189` (page 58) a une filière vide à renseigner.
Soupçons non vérifiés : `PUB-026` (homologue probable page 42), `PUB-049`
(homologue probable page 24). Correction et rétablissement : E3.5.

## Suivi E3.4 : relecture faculte_classique (issue #23)

Colonne produite par `python scripts/make_faculte_classique.py --output
data/faculte_classique.csv` (règle : `Établissement` commence par
« Faculté » → `oui`, sinon `non` ; 3 exceptions relues ci-dessous).
224 lignes : 62 `oui`, 162 `non`. Consigne source, guide page 9 : « Il
est fortement recommandé de choisir au moins une formation dans une
Faculté Classique parmi les trois choix à opérer sur la plateforme. »

Relecture : les 65 lignes marquées `oui` par la règle (59 ouvertes à
C/D selon `series_et_offres_2026_2027.csv`, plus `PUB-145`
« Toutes séries » sans couple C/D dans l'index), regroupées en
14 libellés, tous de vraies facultés universitaires (FA, FADESP, FASHS,
FASEG ×2, FLLAC, FLASH, FLASH-Adjarra, FM, FSA, FAST,
FAST/Natitingou, FDSP, FSS).

Exceptions (`oui` → `non`, dans `REVIEWED_EXCEPTIONS` du script) :
`PUB-186`, `PUB-187`, `PUB-188` — le PDF montre l'Institut National
Supérieur de Technologie Industrielle (INSTI) aux pages 57, 59 et 58
(Génie Civil 50/10 ; Génie Électrique et Informatique 25/5, les deux
options) alors que le CSV porte encore le libellé FAST/Natitingou mis
en quarantaine en E3.2. E3.5 corrige les libellés, après quoi ces
exceptions rejoignent la règle : régénérer le fichier.

Lignes en quarantaine (E3.2) restant `oui`, l'établissement vrai étant
toujours une faculté : `PUB-045` (FLASH-Adjarra, page 23), `PUB-048`
(FLLAC, page 24), `PUB-142` (FLASH-Parakou, page 53). `PUB-025`
(ENSTIC, vrai ENS) reste `non`.

Pièges vérifiés `non` : `PUB-002` (CIFRED, « Facultaire » dans le nom
mais un centre), `PUB-211` à `PUB-215` (UFR de l'UADC, pas des
facultés), `PUB-195`/`PUB-210` (établissement vide), `PUB-216`
(libellé de filière décalé, « Métiers de l'agriculture »).

Soupçons hors périmètre, non touchés (filière improbable pour la
faculté, sans effet sur cette colonne) : `PUB-130` (Droit Privé, FA),
`PUB-053`/`054`/`055` (filières agricoles, FLLAC), `PUB-141`
(Allemand, FASEG). À signaler en E3.5.

## Conclusion

Échantillon graine 2026 : 15 lignes sur 20 intégralement conformes,
5 écarts documentés (§1 à §5). Seuil franchi : `docs/decisions.md`
tranche (corriger + restreindre, en E3.5). Le mot « vérifié » ne couvre
que les valeurs transcrites du guide ; les cellules « – » sont dites
« non publiées par le guide », jamais affirmées. Aucune modification de
`data/` dans cette story.
