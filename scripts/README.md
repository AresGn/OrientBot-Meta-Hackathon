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

## Colonne faculte_classique (E3.4)

```bash
python scripts/make_faculte_classique.py --output data/faculte_classique.csv
```

Produit `data/faculte_classique.csv` (`Offre_ID`, `faculte_classique`
`oui`/`non`) depuis les offres recommandables du guide (`OK` à page établie) : `oui` quand l'établissement
commence par « Faculté », 3 exceptions relues à la main (`PUB-186`,
`PUB-187`, `PUB-188`, vrai établissement INSTI, pages 57/59/58 du PDF).
Sans `--output`, le CSV part sur la sortie standard (le test
`tests/test_faculte_classique.py` le compare au fichier commité). À
régénérer après la réparation des libellés en E3.5, puis retirer les exceptions devenues redondantes (avertissement sur stderr ; un libellé réparé qui contredirait la revue fait échouer le script).
