LABORATOIRE VIRTUEL D'ELECTROTECHNIQUE — VERSION CABLAGE INDUSTRIEL
====================================================================

CONTENU
- app.py : application Streamlit complète, basée sur le fichier fourni.
- requirements.txt : dépendances du projet.
- assets/composants/ : dossier des photographies locales des matériels.

INSTALLATION
1. Décompresser le ZIP dans le dépôt du projet.
2. Conserver les fichiers Excel de votre application à côté de app.py :
   - Liste des étudiants_2026-2027.xlsx
   - dataEDT-ELT-S1-2027.xlsx
3. Installer les dépendances : pip install -r requirements.txt
4. Lancer : streamlit run app.py

CABLAGE COLORÉ
Dans « Éditeur graphique de circuits » :
- placer les appareils dans le canevas ;
- relier les poignées des appareils ;
- choisir les bornes de départ et d'arrivée ;
- sélectionner la couleur/fonction de chaque conducteur ;
- consulter le schéma coloré généré sous le canevas.

La convention proposée est pédagogique : phases noir/marron, neutre bleu,
commande rouge, PE vert/jaune, signaux orange et autres conducteurs jaune.
Elle doit être adaptée aux normes, au type de circuit et aux consignes de sécurité
applicables dans votre laboratoire. Le vert/jaune est réservé au conducteur PE.

PHOTOGRAPHIES REELLES
Le code prévoit un fichier JPG local par composant dans assets/composants/.
Exemples de noms :
- moteur-asynchrone-triphase.jpg
- contacteur-km1.jpg
- relais-thermique.jpg
- disjoncteur-tripolaire.jpg
- bouton-poussoir-no.jpg
- bouton-poussoir-nf.jpg

IMPORTANT : le dossier de photos est fourni vide volontairement. Aucune image
générée ou photo d'un autre matériel n'est présentée comme une photographie réelle
du composant. Ajoutez des photos prises dans votre atelier ou des images dont la
licence autorise la redistribution, puis conservez leurs crédits dans
SOURCES_PHOTOS.txt.

DONNEES ET VALIDATION
Les corrigés et circuits sont pédagogiques. Avant tout usage sur matériel réel,
faites valider les schémas, calibres, protections, sections de conducteurs et
procédures de consignation par l'enseignant responsable. Le simulateur ne remplace
pas une vérification électrique réglementaire.
