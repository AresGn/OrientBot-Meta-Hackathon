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
