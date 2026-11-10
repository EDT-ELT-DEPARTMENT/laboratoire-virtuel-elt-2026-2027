# Laboratoire virtuel ELT — identification par matricule et TP filtrés depuis l'EDT

## Fichiers à conserver ensemble
- `app.py`
- `requirements.txt`
- `dataEDT-ELT-S1-2027.xlsx`
- `Liste des étudiants_2026-2027.xlsx`

## Fonctionnement étudiant
1. L'étudiant saisit son `Mat. Etudiant` dans la barre latérale.
2. L'application recherche ce matricule dans l'onglet `Feuille1` du fichier des étudiants.
3. Le nom, le prénom, la promotion, le groupe et le sous-groupe sont affichés automatiquement.
4. L'application filtre les lignes de l'EDT par promotion, puis par groupe/sous-groupe.
5. Seuls les enseignements TP correspondants sont proposés dans `Choisir le travail pratique`.
6. Les enseignants associés au TP choisi sont affichés automatiquement, avec les horaires et lieux disponibles.

## Déploiement
Déposez les quatre fichiers à la racine du dépôt GitHub connecté à Streamlit Cloud. Le nom des deux fichiers Excel doit être conservé exactement comme indiqué ci-dessus.

## Important
La liste des TP est entièrement alimentée par l'EDT. Les schémas de simulation interactifs ne sont actuellement disponibles que pour les quatre modèles déjà présents dans `TPS` (moteur direct, pont de Graetz, circuit RC, Arduino). Pour les autres TP, l'application affiche le TP et ses enseignants, mais indique qu'il faut encore définir le schéma pédagogique correspondant.
