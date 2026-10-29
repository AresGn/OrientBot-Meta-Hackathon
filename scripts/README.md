# scripts

## Tranche verticale sans vision ni voix (E2.5)

Commande (depuis la racine du dépôt, sans clé ni API) :

```bash
python scripts/run_vertical_slice.py data/samples/vertical_slice_serie_d.json
```

Lit la fixture JSON (notes série D + profil fictifs), calcule les moyennes de
classement par `compute_ranking_average`, filtre les offres par la recherche
provisoire (`Statut_qualité = OK` + `Bac_recommandé`, remplacée par E3.5),
construit un brouillon avec preuves et l'imprime seulement si `verify_report`
renvoie une liste vide. Code de sortie 1, sans rapport imprimé, si le
vérificateur refuse le brouillon.

Test d'intégration associé : `python -m pytest -q tests/test_vertical_slice.py`.

## Tirage de l'audit de données (E3.3)

```bash
python scripts/sample_audit.py --seed 2026
```

Affiche 20 `Offre_ID` de lignes `Statut_qualité = OK`, un par ligne, dans
l'ordre du tirage. Relancer avec la même graine donne les mêmes 20 lignes
(test : `tests/test_sample_audit.py`). L'audit comparant ces lignes au PDF
est publié dans `docs/data-audit.md`.
