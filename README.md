# Laboratoire virtuel — Électrotechnique

Application Streamlit de travaux pratiques virtuels.

## Lancer en local

```bash
python -m pip install -r requirements.txt
streamlit run app.py
```

## Déploiement Streamlit Community Cloud

1. Créer un dépôt GitHub pour le projet.
2. Ajouter `app.py` et `requirements.txt` à la racine du dépôt.
3. Ouvrir https://share.streamlit.io/ et connecter le compte GitHub.
4. Choisir le dépôt, la branche et `app.py` comme fichier principal.
5. Déployer.

## À compléter avant usage officiel

- Authentification sécurisée et rôles étudiant/enseignant/administrateur.
- Persistance des résultats dans une base de données.
- Validation pédagogique des corrigés et des modèles physiques.
- Éditeur graphique de schémas et de câblage.
- Communication matérielle sécurisée pour les équipements réels.

## Éditeur graphique de circuits

L'éditeur utilise Streamlit Flow / React Flow : composants déplaçables, fils créés
entre les composants, sélection des bornes de chaque fil et correction de la topologie.
La simulation est actuellement logique/pédagogique et ne calcule pas encore les tensions,
courants ou puissances. Aucun matériel réel n'est commandé.


## Calculs électriques (modèles physiques)

Dans l'éditeur graphique, le TP sélectionné affiche aussi un modèle numérique adapté :
- moteur triphasé : puissance absorbée, P/Q/S, courant nominal, courant de démarrage estimé et couple ;
- pont de Graetz résistif : forme d'onde, tension moyenne/efficace, courant et puissance ;
- circuit RC : constante de temps, tension et courant en charge/décharge ;
- LED sur GPIO : résistance série, courant et dissipation.

Les résultats sont calculés à partir des paramètres entrés. Ce sont des modèles analytiques
de niveau pédagogique, avec hypothèses explicites. Ils ne remplacent pas un solveur général
SPICE ni une simulation dynamique complète de machine asynchrone.

## Solveur électrique DC (nouvelle étape)

Le canevas accepte maintenant plusieurs instances d'un même composant. Les blocs affichent
les noms de leurs bornes sous forme de repères visibles. Chaque fil du canevas est affecté
à une borne de départ et une borne d'arrivée dans le panneau de configuration des fils.
La bibliothèque inclut une source de tension DC et une source de courant DC. Les fils
fusionnent les bornes en nœuds électriques ; l'étudiant choisit un nœud de référence (0 V),
renseigne les valeurs des composants, puis lance la résolution.

Le solveur utilise la méthode des nœuds modifiée (MNA) et fournit les tensions de nœuds,
les courants orientés et les puissances absorbées/fournies pour les résistances et sources
DC idéales. Les appareils de mesure virtuels affichent la différence de potentiel entre
deux bornes choisies ou le courant calculé dans un composant. Les sources de tension sont
orientées de « + » vers « - » ; le courant des sources de courant est défini dans le même sens.

**Limites actuelles :** circuits linéaires en régime continu uniquement. Les bornes sont
visibles sur les blocs, mais cette version de Streamlit Flow ne permet pas encore de tirer
un fil directement depuis une broche individuelle : l'étudiant relie les blocs dans le canevas,
puis choisit les deux broches exactes dans les listes déroulantes. Les diodes,
transistors, condensateurs, bobines, transformateurs, contacteurs et moteurs ne sont pas
encore intégrés à ce solveur. Les modèles analytiques spécifiques aux TP restent séparés
et ne doivent pas être confondus avec la résolution du circuit dessiné. Pour les circuits
AC, transitoires et non linéaires, une étape ultérieure devra intégrer un moteur SPICE
(par exemple ngspice) ou étendre le solveur avec des modèles validés.
