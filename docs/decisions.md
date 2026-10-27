# Décisions

Tâches hors périmètre jugées indispensables, ou choix qui s'écartent du PRD (`docs/prd.md`). Rien de hors périmètre n'est implémenté avant le gel du 3 novembre.

| Date | Décision | Raison |
|---|---|---|
| 2026-10-27 | Projet renommé **PathProof** (dépôt `PathProof-Meta-Hackathon`) ; piste Indie Developer | Positionnement « chaque parcours a sa preuve » (`docs/prd.md` section 0) |
| 2026-10-27 | Le PDF du guide 2026-2027 reste en local (`data/source/`, ignoré par git) | Mention « Vente interdite » ; pas d'URL officielle publique trouvée. Voir `docs/prd.md` section 6, point 4 |
| 2026-10-27 | `offres_privees_2026_2027.csv` (753 lignes) non copié dans `data/` | Inutilisé pour recommander (ni série, ni matières, ni débouchés) ; moins de contenu du guide republié. Mentionné dans le README |
| 2026-10-27 | `coefficients_bac_benin.json` copié sans modification, y compris le champ `recommandation` (note annexe qui contient le mot « chatbot ») | Le fichier reste identique à sa source. À décider : supprimer ce champ, car le PRD interdit de reprendre cette phrase. Aucun code ne le lit |
| 2026-10-27 | `env` ajouté au `.gitignore` | Un fichier `env` (sans point) contenant `MUSE_API_KEY` existait à la racine, non ignoré. Le bon nom est `.env` |
| 2026-10-27 | RIASEC retiré | Un profil de personnalité ne se prouve pas ; fait « chatbot » (`docs/prd.md` section 2.2) |
| 2026-10-27 | `data/filieres.csv` (gabarit vide) et le test associé à remplacer | Les CSV du guide 2026-2027 sont la nouvelle source ; `lookup_filieres` lit encore l'ancien schéma |
