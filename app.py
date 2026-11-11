# -*- coding: utf-8 -*-
"""
Plateforme de Travaux Pratiques Virtuels - Département d'Électrotechnique
Application Streamlit autonome.
"""
from __future__ import annotations

import io
import math
import base64
import mimetypes
import os
import hmac
from datetime import datetime
from uuid import uuid4
from html import escape as html_escape

try:
    from streamlit_flow import streamlit_flow
    from streamlit_flow.elements import StreamlitFlowNode, StreamlitFlowEdge
    from streamlit_flow.state import StreamlitFlowState
    STREAMLIT_FLOW_DISPONIBLE = True
except Exception:
    STREAMLIT_FLOW_DISPONIBLE = False

import numpy as np
import pandas as pd


def _np_integrale_trapezes(valeurs, abscisses):
    """Intégration trapézoïdale compatible avec NumPy ancien et récent."""
    fonction = getattr(np, "trapezoid", None)
    if fonction is None:  # Compatibilité avec les anciennes versions de NumPy.
        fonction = getattr(np, "trapz", None)
    if fonction is None:
        raise RuntimeError(
            "La version de NumPy installée ne fournit ni trapezoid ni trapz. "
            "Mettez NumPy à jour."
        )
    return fonction(valeurs, abscisses)
import plotly.graph_objects as go
import streamlit as st

# ---------------------------------------------------------------------
# CORRESPONDANCE ÉTUDIANTS <-> EDT (matricule, promotion, groupe, sous-groupe)
# ---------------------------------------------------------------------
from pathlib import Path
import re
import unicodedata

BASE_DIR_LAB = Path(__file__).resolve().parent
FICHIER_ETUDIANTS_LAB = BASE_DIR_LAB / "Liste des étudiants_2026-2027.xlsx"
FICHIER_EDT_LAB = BASE_DIR_LAB / "dataEDT-ELT-S1-2027.xlsx"


def _lab_nettoyer_texte(valeur):
    if valeur is None or (isinstance(valeur, float) and pd.isna(valeur)):
        return ""
    texte = str(valeur).strip()
    if texte.lower() in {"nan", "none", "nat"}:
        return ""
    return re.sub(r"\s+", " ", texte)


def _lab_normaliser(valeur):
    texte = _lab_nettoyer_texte(valeur)
    texte = unicodedata.normalize("NFKD", texte)
    texte = "".join(c for c in texte if not unicodedata.combining(c))
    return re.sub(r"\s+", "", texte).upper()


def _lab_normaliser_matricule(valeur):
    texte = _lab_nettoyer_texte(valeur)
    if re.fullmatch(r"\d+\.0", texte):
        texte = texte[:-2]
    return re.sub(r"\s+", "", texte)


@st.cache_data(show_spinner=False)
def _lab_charger_etudiants(chemin_fichier):
    df = pd.read_excel(chemin_fichier, sheet_name="Feuille1", dtype=str)
    df.columns = [_lab_nettoyer_texte(c) for c in df.columns]
    colonnes_requises = ["Mat. Etudiant", "Nom", "Prénom", "Promotion", "Groupe", "Sous groupe"]
    manquantes = [c for c in colonnes_requises if c not in df.columns]
    if manquantes:
        raise ValueError("Colonnes absentes du fichier étudiants : " + ", ".join(manquantes))
    for c in colonnes_requises:
        df[c] = df[c].map(_lab_nettoyer_texte)
    df["_mat_norm"] = df["Mat. Etudiant"].map(_lab_normaliser_matricule)
    df["_promo_norm"] = df["Promotion"].map(_lab_normaliser)
    df = df[df["_mat_norm"].ne("")].copy()
    return df


@st.cache_data(show_spinner=False)
def _lab_charger_edt(chemin_fichier):
    df = pd.read_excel(chemin_fichier, sheet_name=0, dtype=str)
    df.columns = [_lab_nettoyer_texte(c) for c in df.columns]
    requis = ["Enseignements", "Code", "Enseignants", "Horaire", "Jours", "Lieu", "Promotion"]
    manquantes = [c for c in requis if c not in df.columns]
    if manquantes:
        raise ValueError("Colonnes absentes du fichier EDT : " + ", ".join(manquantes))
    for c in requis:
        df[c] = df[c].map(_lab_nettoyer_texte)
    df["_promo_norm"] = df["Promotion"].map(_lab_normaliser)
    df["_code_norm"] = df["Code"].map(_lab_normaliser)
    df["_enseignement_norm"] = df["Enseignements"].map(_lab_normaliser)
    # On retient les lignes dont le code est TP ou dont l'intitulé commence par TP.
    masque_tp = df["_code_norm"].eq("TP") | df["_enseignement_norm"].str.startswith("TP-")
    df = df[masque_tp & df["Enseignements"].ne("")].copy()
    return df


def _lab_retrouver_etudiant(matricule, df_etudiants):
    mat = _lab_normaliser_matricule(matricule)
    if not mat:
        return None, "Saisissez votre matricule étudiant."
    correspondances = df_etudiants[df_etudiants["_mat_norm"].eq(mat)]
    if correspondances.empty:
        return None, "Aucun étudiant ne correspond à ce matricule dans la liste officielle."
    if len(correspondances) > 1:
        return None, "Ce matricule apparaît plusieurs fois dans la liste. Contactez l'administration."
    etu = correspondances.iloc[0]
    if not etu.get("Promotion", "").strip():
        return None, "La promotion de cet étudiant n'est pas renseignée dans le fichier officiel."
    return etu, ""


def _lab_groupe_depuis_sous_groupe(sous_groupe):
    sg = _lab_normaliser(sous_groupe)
    match = re.match(r"SG(\d+)", sg)
    if not match:
        return ""
    chiffres = match.group(1)
    return "G" + chiffres[:-1] if len(chiffres) >= 2 else ""


def _lab_tp_correspond_au_groupe(intitule, groupe, sous_groupe):
    """Accepte TP global, TP du sous-groupe exact et TP partagé SG11/SG12."""
    texte = _lab_normaliser(intitule)
    groupes_sg = re.findall(r"SG\d+", texte)
    g = _lab_normaliser(groupe)
    sg = _lab_normaliser(sous_groupe)
    if not groupes_sg:
        return True
    if sg and sg not in {"P", "PROMOTION"}:
        if sg in groupes_sg:
            return True
        # Un TP partagé (ex. SG11/SG12) est retenu seulement si le sous-groupe exact y figure.
        return False
    # Si le fichier étudiant ne fournit pas de sous-groupe, on filtre au moins par groupe.
    numero = re.search(r"\d+", g)
    if numero:
        prefixe = "SG" + numero.group(0)
        return any(x.startswith(prefixe) for x in groupes_sg)
    return False


def _lab_tp_etudiant(etu, df_edt):
    promo = _lab_normaliser(etu.get("Promotion", ""))
    groupe = _lab_nettoyer_texte(etu.get("Groupe", ""))
    sous_groupe = _lab_nettoyer_texte(etu.get("Sous groupe", ""))
    lignes = df_edt[df_edt["_promo_norm"].eq(promo)].copy()
    if lignes.empty:
        return lignes
    lignes = lignes[
        lignes["Enseignements"].map(
            lambda x: _lab_tp_correspond_au_groupe(x, groupe, sous_groupe)
        )
    ].copy()
    return lignes


def _lab_modele_simulation_depuis_tp(intitule):
    """Relie les intitulés EDT aux modèles effectivement présents dans TPS."""
    t = _lab_normaliser(intitule)
    if "ARDUINO" in t:
        return "Commande d'un moteur par Arduino"
    if "GRAETZ" in t or "REDRESSEMENT" in t:
        return "Redressement monophasé - Pont de Graetz"
    if re.search(r"\bRC\b", t) or "CIRCUITRC" in t:
        return "Mesure des caractéristiques d'un circuit RC"
    if "MOTEUR" in t and ("DEMARRAGE" in t or "DIRECT" in t):
        return "Démarrage direct d'un moteur asynchrone"
    return None

# ---------------------------------------------------------------------
# CONFIGURATION GÉNÉRALE
# ---------------------------------------------------------------------
st.set_page_config(
    page_title="Laboratoire virtuel - Électrotechnique",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

TITRE_OFFICIEL = (
    "Plateforme de gestion des EDTs-Semestre 01-2026-2027_"
    "Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA"
)

st.markdown(
    """
    <style>
    .main-title {font-size: 1.55rem; font-weight: 750; color: #145a8d;
                 line-height: 1.35; margin-bottom: .25rem;}
    .sub-title {color: #64748b; font-size: .95rem; margin-bottom: 1rem;}
    .section-title {font-size: 1.2rem; font-weight: 700; color: #145a8d;}
    div[data-testid="stMetric"] {background: rgba(30, 136, 229, .06);
        border: 1px solid rgba(30, 136, 229, .18); padding: 12px;
        border-radius: 10px;}
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------
# BIBLIOTHÈQUE DE COMPOSANTS
# Les bornes sont des noms logiques utilisés pour contrôler le câblage.
# ---------------------------------------------------------------------
COMPOSANTS = {
    "Appareils de mesure & contrôle": {
        "Voltmètre": ["V+", "V-"],
        "Ampèremètre": ["A+", "A-"],
        "Multimètre": ["COM", "VΩ", "A"],
        "Oscilloscope": ["CH1+", "CH1-", "CH2+", "CH2-", "GND"],
        "Wattmètre": ["U+", "U-", "I+", "I-"],
        "Tachymètre": ["Entrée", "GND"],
    },
    "Puissance & actionneurs": {
        "Moteur asynchrone triphasé": ["U1", "V1", "W1", "U2", "V2", "W2", "PE"],
        "Transformateur monophasé": ["P1", "P2", "S1", "S2"],
        "Contacteur KM1": ["L1", "L2", "L3", "T1", "T2", "T3", "A1", "A2", "13", "14"],
        "Relais thermique": ["L1", "L2", "L3", "T1", "T2", "T3", "95", "96"],
        "Pont de diodes (Graetz)": ["AC1", "AC2", "DC+", "DC-"],
        "Diode de puissance": ["Anode", "Cathode"],
        "Résistance de puissance": ["Borne 1", "Borne 2"],
        "Source de tension DC": ["+", "-"],
        "Source de courant DC": ["+", "-"],
        "Lampe": ["L", "N"],
    },
    "Commande, signalisation & sécurité": {
        "Bouton poussoir NO": ["13", "14"],
        "Bouton poussoir NF": ["11", "12"],
        "Arrêt d'urgence NF": ["11", "12"],
        "Voyant lumineux": ["X1", "X2"],
        "Fusible": ["Entrée", "Sortie"],
        "Disjoncteur tripolaire": ["L1", "L2", "L3", "T1", "T2", "T3"],
        "Relais auxiliaire": ["A1", "A2", "13", "14", "21", "22"],
    },
    "Capteurs & transducteurs": {
        "Capteur inductif": ["BN (+24V)", "BU (0V)", "BK (Sortie)"],
        "Capteur optique": ["BN (+24V)", "BU (0V)", "BK (Sortie)"],
        "Codeur incrémental": ["+V", "0V", "A", "B", "Z"],
        "Sonde de température": ["Signal+", "Signal-"],
    },
    "Électronique de base & analogique": {
        "Résistance": ["A", "B"],
        "Condensateur": ["A", "B"],
        "Bobine": ["A", "B"],
        "Transistor NPN": ["Base", "Collecteur", "Émetteur"],
        "Amplificateur opérationnel": ["V+", "V-", "Entrée+", "Entrée-", "Sortie"],
        "LED": ["Anode", "Cathode"],
        "Potentiomètre": ["A", "Curseur", "B"],
    },
    "Microcontrôleurs & systèmes": {
        "Arduino Uno": ["5V", "GND", "D2", "D3", "D4", "D5", "A0", "A1"],
        "ESP32": ["3V3", "GND", "GPIO18", "GPIO19", "GPIO21", "GPIO22", "GPIO34"],
        "API Siemens (E/S)": ["L+", "M", "I0.0", "I0.1", "Q0.0", "Q0.1"],
    },
}


# ---------------------------------------------------------------------
# FICHES TECHNIQUES ET PHOTOGRAPHIES LOCALES
# Les valeurs nominales dépendent de la référence exacte du fabricant :
# elles ne sont volontairement pas inventées lorsqu'elles ne sont pas connues.
# ---------------------------------------------------------------------
# Les illustrations génériques sont déposées directement à la racine du dépôt
# GitHub (à côté de app.py). Les illustrations propres à une marque, si elles
# existent, restent prioritaires dans assets/composants/<marque>/.
DOSSIER_PHOTOS_COMPOSANTS = BASE_DIR_LAB / "assets" / "composants"
DOSSIER_PHOTOS_RACINE = BASE_DIR_LAB
MARQUES_COMPOSANTS = {
    "Schneider Electric": "schneider-electric",
    "ABB": "abb",
    "Siemens": "siemens",
}


def _chemin_photo_composant(nom, marque="Schneider Electric"):
    """Recherche une photo d'abord à la racine du dépôt, quel que soit son format.

    Les noms sont comparés après normalisation : espaces, tirets, accents et
    underscores sont donc équivalents. Les sous-dossiers de marque restent
    acceptés en solution de repli pour préserver la compatibilité.
    """
    slug = _slug_composant(nom)
    dossier_marque = MARQUES_COMPOSANTS.get(marque, "schneider-electric")
    extensions = (".jpg", ".jpeg", ".png", ".webp", ".JPG", ".JPEG", ".PNG", ".WEBP")

    # 1) Fichiers placés directement à côté de app.py : emplacement du dépôt.
    for extension in extensions:
        chemin = DOSSIER_PHOTOS_RACINE / f"{slug}{extension}"
        if chemin.is_file():
            return chemin

    # 2) Recherche par nom normalisé à la racine : accepte par exemple
    #    "Moteur asynchrone triphasé.PNG" ou "moteur_asynchrone_triphasé.jpg".
    try:
        fichiers_racine = [f for f in DOSSIER_PHOTOS_RACINE.iterdir()
                           if f.is_file() and f.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")]
    except OSError:
        fichiers_racine = []

    correspondances = []
    for fichier in fichiers_racine:
        nom_image = _slug_composant(fichier.stem)
        if nom_image == slug:
            correspondances.append((0, fichier))
        elif len(slug) >= 7 and (slug in nom_image or nom_image in slug):
            # Tolère un suffixe/prefixe descriptif dans le nom de l'image,
            # sans sélectionner des noms très courts et ambigus.
            correspondances.append((abs(len(nom_image) - len(slug)), fichier))
    if correspondances:
        correspondances.sort(key=lambda element: (element[0], element[1].name.lower()))
        return correspondances[0][1]

    # 3) Compatibilité : anciennes images rangées dans le dossier de marque.
    dossier_marque_path = DOSSIER_PHOTOS_COMPOSANTS / dossier_marque
    for extension in extensions:
        chemin = dossier_marque_path / f"{slug}{extension}"
        if chemin.is_file():
            return chemin

    # Chemin attendu conservé pour permettre au reste de l'interface d'afficher
    # un message explicatif si aucune illustration n'existe.
    return DOSSIER_PHOTOS_RACINE / f"{slug}.jpg"

DESCRIPTIONS_COMPOSANTS = {
    "Moteur asynchrone triphasé": ("Convertit l'énergie électrique triphasée en énergie mécanique par induction électromagnétique.", "Moteur triphasé", "Plaque signalétique : tension, couplage Δ/Y, puissance, courant, fréquence, cos φ, rendement et vitesse.", "U1, V1, W1 : début des enroulements ; U2, V2, W2 : fins ; PE : terre de protection.", "Entraînement de pompes, ventilateurs, convoyeurs et machines industrielles."),
    "Transformateur monophasé": ("Transfère l'énergie alternative entre deux circuits par induction électromagnétique.", "Transformateur", "Plaque : puissances apparente (VA), tensions primaire/secondaire, fréquence et courant nominal.", "P1-P2 : primaire ; S1-S2 : secondaire.", "Adaptation de tension, isolation galvanique et alimentation de montages."),
    "Contacteur KM1": ("Appareil électromécanique commandé par une bobine permettant d'établir ou couper un circuit de puissance.", "Contacteur", "Tension bobine A1-A2, tension assignée, courant d'emploi, catégorie d'emploi (ex. AC-3) et nombre de pôles selon référence.", "L1/L2/L3 : arrivée ; T1/T2/T3 : départ ; A1/A2 : bobine ; 13-14 : auxiliaire NO.", "Commande fréquente de moteurs et de charges électriques."),
    "Relais thermique": ("Protège un moteur contre les surcharges prolongées en détectant l'échauffement lié au courant.", "Relais thermique", "Plage de réglage en ampères, classe de déclenchement, tension/courant des contacts auxiliaires selon référence.", "L1/L2/L3 : entrée ; T1/T2/T3 : sortie ; 95-96 : contact NF de défaut.", "Protection contre les surcharges moteur, généralement associé à un contacteur."),
    "Pont de diodes (Graetz)": ("Redresse une tension alternative monophasée en tension continue ondulée.", "Pont redresseur", "Tension inverse répétitive, courant moyen admissible, courant de surcharge et chute directe selon référence.", "AC1-AC2 : entrée alternative ; DC+ et DC- : sortie continue.", "Alimentations continues et redresseurs monophasés."),
    "Diode de puissance": ("Laisse principalement passer le courant dans le sens anode vers cathode et bloque en sens inverse.", "Diode", "Courant direct, tension inverse répétitive, chute directe et courant de surtension selon référence.", "Anode (A) et cathode (K, côté bague sur diode axiale).", "Redressement, roue libre et protection contre les inversions de polarité."),
    "Résistance": ("Limite le courant et crée une chute de tension selon la loi d'Ohm.", "Résistance", "Valeur en ohms, tolérance, puissance dissipable et tension maximale selon référence.", "Deux bornes non polarisées A et B.", "Limitation de courant, diviseur de tension et polarisation."),
    "Résistance de puissance": ("Dissipe de l'énergie électrique sous forme de chaleur tout en limitant le courant.", "Résistance", "Valeur (Ω), puissance nominale (W), tolérance et conditions de refroidissement selon référence.", "Deux bornes non polarisées.", "Charges, freinage, limitation de courant et dissipation."),
    "Condensateur": ("Stocke temporairement l'énergie dans un champ électrique et s'oppose aux variations rapides de tension.", "Condensateur", "Capacité (F), tension nominale, tolérance, technologie et polarité éventuelle.", "Deux bornes ; respecter + et - pour un condensateur polarisé.", "Filtrage, temporisation, couplage et circuits RC."),
    "Bobine": ("Stocke l'énergie dans un champ magnétique et s'oppose aux variations de courant.", "Bobine", "Inductance (H), courant admissible, résistance série et fréquence d'utilisation.", "Deux bornes A et B ; polarité généralement non imposée pour une bobine simple.", "Filtrage, relais, électroaimants et circuits RL."),
    "Transistor NPN": ("Composant semi-conducteur permettant l'amplification ou la commutation d'un courant.", "Transistor NPN", "Référence, tension collecteur-émetteur, courant collecteur, puissance et gain selon datasheet.", "Base (B), collecteur (C), émetteur (E).", "Commande de relais, commutation et amplification."),
    "Amplificateur opérationnel": ("Amplifie la différence de tension entre ses entrées selon son alimentation et sa contre-réaction.", "Amplificateur opérationnel", "Alimentation, tension d'offset, bande passante, slew-rate et plage de mode commun selon référence.", "V+ et V- : alimentation ; Entrée+ et Entrée- ; Sortie.", "Amplification, comparateur (selon montage), filtrage et conditionnement analogique."),
    "LED": ("Émet de la lumière lorsqu'elle est parcourue par un courant direct.", "LED", "Couleur/longueur d'onde, courant direct, tension directe et puissance selon référence.", "Anode (+) et cathode (-, patte courte/ méplat selon boîtier).", "Signalisation et indication d'état ; utiliser une limitation de courant."),
    "Potentiomètre": ("Résistance variable à trois bornes avec un curseur mobile.", "Potentiomètre", "Résistance totale, loi (linéaire/logarithmique), puissance et angle de rotation.", "A et B : extrémités ; Curseur : borne mobile.", "Réglage de niveau, consigne et diviseur de tension."),
    "Arduino Uno": ("Carte à microcontrôleur programmable pour acquisition et commande de signaux.", "Carte Arduino", "Carte exacte, microcontrôleur, tension logique, limites de courant E/S et alimentation selon version.", "5V, GND, broches numériques et entrées analogiques ; respecter les limites électriques.", "Prototypage, commande basse tension et acquisition pédagogique."),
    "ESP32": ("Microcontrôleur avec connectivité sans fil intégrée pour systèmes embarqués.", "Carte ESP32", "Modèle de module, alimentation 3,3 V, limites GPIO, Wi-Fi/Bluetooth selon datasheet.", "3V3, GND et GPIO ; les entrées ne sont généralement pas tolérantes au 5 V.", "Objets connectés, commande et mesure."),
    "API Siemens (E/S)": ("Automate programmable industriel assurant le traitement logique des entrées et sorties.", "Automate programmable", "Référence CPU/module, tension d'alimentation, type d'E/S, courant par voie et protocole selon modèle.", "L+/M : alimentation ; I : entrées ; Q : sorties.", "Automatisation de procédés et commande de machines."),
}
# Fallback fiches by type/category
def _fiche_generique(nom, categorie):
    if "mesure" in categorie.lower() or nom in ("Voltmètre", "Ampèremètre", "Multimètre", "Oscilloscope", "Wattmètre", "Tachymètre"):
        return ("Instrument destiné à mesurer ou observer une grandeur électrique ou mécanique.", "Instrument de mesure", "Plage, précision, catégorie de sécurité et bande passante selon modèle.", "Bornes d'entrée et référence indiquées sur l'appareil ; respecter les catégories de mesure.", "Contrôle, diagnostic et caractérisation expérimentale.")
    if "capteur" in categorie.lower():
        return ("Détecte une grandeur physique et la convertit en signal exploitable.", "Capteur", "Alimentation, portée/plage, type de sortie, précision et temps de réponse selon référence.", "Alimentation, 0 V et sortie ; vérifier le brochage constructeur.", "Acquisition de présence, position, vitesse ou température.")
    if "commande" in categorie.lower():
        return ("Organe de commande, de signalisation ou de protection d'un circuit.", "Commande électrique", "Tension assignée, courant admissible, catégorie d'emploi et degré de protection selon référence.", "Repères normalisés indiqués dans la fiche ; vérifier le schéma constructeur.", "Commande, signalisation et sécurité des installations.")
    return ("Composant utilisé dans les circuits électriques ou électroniques.", "Composant électrique", "Caractéristiques nominales à relever sur le marquage et la documentation constructeur.", "Bornes selon le repérage indiqué sur le composant.", "Montage, commande, mesure ou conversion d'énergie selon sa fonction.")

SYMBOLES_ELECTRIQUES = {
    "Résistance": "─[ R ]─", "Résistance de puissance": "─[ R ]─",
    "Condensateur": "─| |─", "Bobine": "─((((─", "Diode de puissance": "─|>|─",
    "LED": "─|>|─  ↗↗", "Transistor NPN": "B ─|> C / E",
    "Source de tension DC": "─( + − )─", "Source de courant DC": "─( ↑ )─",
    "Lampe": "─( X )─", "Fusible": "─[ F ]─", "Bouton poussoir NO": "─| |─",
    "Bouton poussoir NF": "─|/|─", "Arrêt d'urgence NF": "─|/|─",
    "Contacteur KM1": "Bobine A1 ─( KM1 )─ A2", "Relais auxiliaire": "Bobine + contacts NO/NF",
    "Relais thermique": "─[ Θ ]─", "Moteur asynchrone triphasé": "─( M 3~ )─",
    "Transformateur monophasé": ")))‖(((", "Pont de diodes (Graetz)": "◇  ~  +  −",
    "Voltmètre": "─( V )─", "Ampèremètre": "─( A )─", "Wattmètre": "─( W )─",
    "Voyant lumineux": "─( ⊗ )─", "Disjoncteur tripolaire": "─o/ o─ ×3",
    "Potentiomètre": "─[↗]─", "Arduino Uno": "┌ Arduino ┐", "ESP32": "┌ ESP32 ┐",
    "API Siemens (E/S)": "┌ API ┐",
}

def _slug_composant(nom):
    texte = unicodedata.normalize("NFKD", str(nom))
    texte = "".join(c for c in texte if not unicodedata.combining(c)).lower()
    return re.sub(r"[^a-z0-9]+", "-", texte).strip("-")

def fiche_composant(nom, categorie, bornes, marque="Schneider Electric"):
    fiche = DESCRIPTIONS_COMPOSANTS.get(nom)
    if fiche is None:
        fiche = _fiche_generique(nom, categorie)
    fonction, symbole, caracteristiques, bornes_desc, utilisation = fiche
    if nom not in DESCRIPTIONS_COMPOSANTS:
        bornes_desc = " ; ".join(bornes) + ". Vérifier le brochage exact sur la documentation constructeur."
    return {
        "fonction": fonction, "symbole": SYMBOLES_ELECTRIQUES.get(nom, f"─[ {symbole} ]─"),
        "caracteristiques": caracteristiques, "bornes": bornes_desc, "utilisation": utilisation,
        "photo": _chemin_photo_composant(nom, marque),
        "marque": marque,
    }

def afficher_photo_composant(nom, fiche, width=None):
    chemin = fiche["photo"]
    if chemin.is_file():
        origine = "illustration spécifique à la marque" if DOSSIER_PHOTOS_COMPOSANTS in chemin.parents else "illustration générique"
        st.image(
            str(chemin),
            caption=f"Illustration pédagogique IA — {fiche['marque']} — {nom} ({origine})",
            use_container_width=True,
        )
    else:
        dossier_marque = MARQUES_COMPOSANTS.get(fiche["marque"], "schneider-electric")
        st.info(
            f"Aucune illustration IA disponible pour **{nom}**. "
            f"Le simulateur a recherché une image nommée comme `{_slug_composant(nom)}` "
            "(JPG, JPEG, PNG ou WEBP) directement à la racine du dépôt, "
            f"puis dans `assets/composants/{dossier_marque}/`. "
            "Ajoutez l'image à l'un de ces emplacements. "
            "Les images sont des illustrations pédagogiques IA non contractuelles : "
            "elles ne représentent pas un modèle commercial exact du fabricant sélectionné."
        )

# ---------------------------------------------------------------------
# TRAVAUX PRATIQUES ET CORRIGÉS DE RÉFÉRENCE
# Chaque liaison est une paire (composant.borne, composant.borne).
# ---------------------------------------------------------------------
TPS = {
    "Démarrage direct d'un moteur asynchrone": {
        "description": "Circuit de puissance et circuit de commande d'un démarrage direct.",
        "composants": [
            "Disjoncteur tripolaire", "Contacteur KM1", "Relais thermique",
            "Moteur asynchrone triphasé", "Bouton poussoir NO",
            "Bouton poussoir NF", "Arrêt d'urgence NF",
        ],
        "liaisons": [
            ("Disjoncteur tripolaire.L1", "Contacteur KM1.L1"),
            ("Disjoncteur tripolaire.L2", "Contacteur KM1.L2"),
            ("Disjoncteur tripolaire.L3", "Contacteur KM1.L3"),
            ("Contacteur KM1.T1", "Relais thermique.L1"),
            ("Contacteur KM1.T2", "Relais thermique.L2"),
            ("Contacteur KM1.T3", "Relais thermique.L3"),
            ("Relais thermique.T1", "Moteur asynchrone triphasé.U1"),
            ("Relais thermique.T2", "Moteur asynchrone triphasé.V1"),
            ("Relais thermique.T3", "Moteur asynchrone triphasé.W1"),
            # Chaîne de commande simplifiée : arrêt d'urgence + arrêt + thermique
            # puis bouton marche et auto-maintien par le contact auxiliaire KM1.
            ("Disjoncteur tripolaire.L1", "Arrêt d'urgence NF.11"),
            ("Arrêt d'urgence NF.12", "Bouton poussoir NF.11"),
            ("Bouton poussoir NF.12", "Relais thermique.95"),
            ("Relais thermique.96", "Bouton poussoir NO.13"),
            ("Relais thermique.96", "Contacteur KM1.13"),
            ("Bouton poussoir NO.14", "Contacteur KM1.A1"),
            ("Contacteur KM1.14", "Contacteur KM1.A1"),
            ("Contacteur KM1.A2", "Disjoncteur tripolaire.L2"),
        ],
    },
    "Redressement monophasé - Pont de Graetz": {
        "description": "Étude d'un redresseur monophasé en pont avec charge résistive.",
        "composants": [
            "Transformateur monophasé", "Pont de diodes (Graetz)",
            "Résistance", "Oscilloscope", "Voltmètre",
        ],
        "liaisons": [
            ("Transformateur monophasé.S1", "Pont de diodes (Graetz).AC1"),
            ("Transformateur monophasé.S2", "Pont de diodes (Graetz).AC2"),
            ("Pont de diodes (Graetz).DC+", "Résistance.A"),
            ("Résistance.B", "Pont de diodes (Graetz).DC-"),
        ],
    },
    "Mesure des caractéristiques d'un circuit RC": {
        "description": "Montage série RC et observation de la tension aux bornes du condensateur.",
        "composants": ["Résistance", "Condensateur", "Oscilloscope", "Multimètre"],
        "liaisons": [
            ("Résistance.B", "Condensateur.A"),
        ],
    },
    "Commande d'un moteur par Arduino": {
        "description": "Commande logique d'une sortie par une carte Arduino (maquette basse tension).",
        "composants": ["Arduino Uno", "LED", "Résistance"],
        "liaisons": [
            ("Arduino Uno.D5", "Résistance.A"),
            ("Résistance.B", "LED.Anode"),
            ("LED.Cathode", "Arduino Uno.GND"),
        ],
    },
}

# ---------------------------------------------------------------------
# ÉTAT DE SESSION
# ---------------------------------------------------------------------
for key, default in {
    "liaisons_etudiant": [],
    "historique": [],
    "dernier_resultat": None,
    "circuit_graphique": None,
    "bornes_par_arete": {},
    "couleurs_fils_par_arete": {},
    "tp_graphique_courant": None,
    "enseignant_authentifie": False,
    "reference_chargee_enseignant": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ---------------------------------------------------------------------
# EN-TÊTE ET IDENTIFICATION
# ---------------------------------------------------------------------
st.markdown(f'<div class="main-title">{TITRE_OFFICIEL}</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-title">Laboratoire numérique • Travaux pratiques • '
    'Simulation pédagogique et analyse expérimentale</div>',
    unsafe_allow_html=True,
)
st.divider()

with st.sidebar:
    st.header("🎓 Identification étudiant")
    matricule_etudiant = st.text_input(
        "Matricule étudiant",
        placeholder="Saisissez votre matricule étudiant",
        key="lab_matricule_etudiant",
        help="Votre identité, promotion, groupe et sous-groupe seront retrouvés automatiquement dans la liste officielle."
    )
    df_etudiants_lab = pd.DataFrame()
    df_edt_lab = pd.DataFrame()
    etudiant_connecte = None
    erreur_identification = ""
    try:
        if not FICHIER_ETUDIANTS_LAB.exists():
            erreur_identification = "Fichier introuvable : Liste des étudiants_2026-2027.xlsx"
        else:
            df_etudiants_lab = _lab_charger_etudiants(str(FICHIER_ETUDIANTS_LAB))
            if matricule_etudiant.strip():
                etudiant_connecte, erreur_identification = _lab_retrouver_etudiant(
                    matricule_etudiant, df_etudiants_lab
                )
        if FICHIER_EDT_LAB.exists():
            df_edt_lab = _lab_charger_edt(str(FICHIER_EDT_LAB))
    except Exception as exc:
        erreur_identification = f"Erreur de lecture des fichiers sources : {exc}"

    if etudiant_connecte is not None:
        nom = _lab_nettoyer_texte(etudiant_connecte.get("Nom", ""))
        prenom = _lab_nettoyer_texte(etudiant_connecte.get("Prénom", ""))
        promotion = _lab_nettoyer_texte(etudiant_connecte.get("Promotion", ""))
        groupe = _lab_nettoyer_texte(etudiant_connecte.get("Groupe", ""))
        sous_groupe = _lab_nettoyer_texte(etudiant_connecte.get("Sous groupe", ""))
        st.success(f"Étudiant reconnu : {prenom} {nom}")
        st.caption(f"Promotion : {promotion}")
        st.caption(f"Groupe : {groupe or 'Non renseigné'}")
        st.caption(f"Sous-groupe : {sous_groupe or 'Non renseigné'}")
    else:
        nom = prenom = promotion = groupe = sous_groupe = ""
        if erreur_identification and matricule_etudiant.strip():
            st.error(erreur_identification)
        else:
            st.info("Saisissez votre matricule pour afficher automatiquement votre groupe et vos TP.")
    st.divider()
    espace = st.radio(
        "Navigation",
        [
            "🏠 Accueil",
            "🧪 Réaliser un TP",
            "🧩 Éditeur graphique de circuits",
            "🧰 Bibliothèque de composants",
            "📈 Mesures réelles & comparaison",
            "👨‍🏫 Espace enseignant",
            "ℹ️ À propos",
        ],
    )
    st.caption("Version pédagogique initiale — données de session non permanentes.")

identite_complete = bool(etudiant_connecte is not None and nom.strip() and prenom.strip() and promotion.strip())


def liste_composants_selectionnes(noms):
    """Construit la liste des bornes sous la forme Composant.Borne."""
    resultat = []
    for categorie, elements in COMPOSANTS.items():
        for composant, bornes in elements.items():
            if composant in noms:
                resultat.extend([f"{composant}.{borne}" for borne in bornes])
    return resultat


def normaliser_liaison(a, b):
    """Une liaison est considérée identique quel que soit son sens."""
    return tuple(sorted((str(a).strip(), str(b).strip())))


def corriger_montage(tp_nom, composants_choisis, liaisons_saisies):
    """Compare les composants et les liaisons au corrigé pédagogique."""
    reference = TPS[tp_nom]
    attendus = set(reference["composants"])
    choisis = set(composants_choisis)
    manquants = sorted(attendus - choisis)
    supplementaires = sorted(choisis - attendus)

    attendues_liaisons = {
        normaliser_liaison(a, b) for a, b in reference["liaisons"]
    }
    saisies_liaisons = {
        normaliser_liaison(a, b) for a, b in liaisons_saisies
        if a and b and a != b
    }
    liaisons_manquantes = sorted(attendues_liaisons - saisies_liaisons)
    liaisons_incorrectes = sorted(saisies_liaisons - attendues_liaisons)

    erreurs = len(manquants) + len(liaisons_manquantes) + len(liaisons_incorrectes)
    total = max(1, len(attendus) + len(attendues_liaisons))
    note = max(0.0, round(20 * (1 - erreurs / total), 2))
    correct = not (manquants or liaisons_manquantes or liaisons_incorrectes)

    details = []
    for c in manquants:
        details.append({"Type": "Composant manquant", "Élément": c, "Correction": "Ajouter ce composant"})
    for c in supplementaires:
        details.append({"Type": "Composant supplémentaire", "Élément": c, "Correction": "Vérifier sa nécessité"})
    for a, b in liaisons_manquantes:
        details.append({"Type": "Liaison manquante", "Élément": f"{a} ↔ {b}", "Correction": "Réaliser cette liaison"})
    for a, b in liaisons_incorrectes:
        details.append({"Type": "Liaison non conforme", "Élément": f"{a} ↔ {b}", "Correction": "Vérifier les bornes de connexion"})

    return {
        "correct": correct,
        "note": 20.0 if correct else note,
        "manquants": manquants,
        "supplementaires": supplementaires,
        "liaisons_manquantes": liaisons_manquantes,
        "liaisons_incorrectes": liaisons_incorrectes,
        "details": details,
    }




def _infos_borne_arete(state, edge):
    """Retourne (id_composant_source, borne_source, id_composant_cible, borne_cible)."""
    nodes = {n.id: n for n in state.nodes}
    a, b = nodes.get(edge.source), nodes.get(edge.target)
    if a is None or b is None:
        return None
    da, db = a.data or {}, b.data or {}
    if da.get("node_role") == "borne" and db.get("node_role") == "borne":
        return da.get("component_id"), da.get("terminal"), db.get("component_id"), db.get("terminal")
    # Compatibilité avec les anciens canevas où le fil reliait directement les blocs.
    ancienne_paire = st.session_state.get("bornes_par_arete", {}).get(edge.id)
    if ancienne_paire and len(ancienne_paire) == 2:
        return edge.source, ancienne_paire[0], edge.target, ancienne_paire[1]
    return edge.source, None, edge.target, None


def _paires_bornes_graphiques(state):
    """Construit automatiquement les bornes de chaque fil à partir des broches reliées."""
    nodes = {n.id: n for n in state.nodes}
    resultat = {}
    for edge in state.edges:
        info = _infos_borne_arete(state, edge)
        if not info:
            continue
        ca, ba, cb, bb = info
        na, nb = nodes.get(ca), nodes.get(cb)
        if na and nb and ba and bb:
            resultat[edge.id] = (ba, bb)
        else:
            resultat[edge.id] = st.session_state.get("bornes_par_arete", {}).get(edge.id)
    return resultat

def initialiser_circuit_graphique():
    if st.session_state.circuit_graphique is None:
        st.session_state.circuit_graphique = StreamlitFlowState(nodes=[], edges=[])


def charger_composants_du_tp_graphique(nom_tp, marque="Schneider Electric"):
    """Place automatiquement dans le canevas tous les appareils requis par le TP.

    Les composants sont chargés sans aucune liaison : le câblage reste entièrement
    à réaliser par l'étudiant.
    """
    tp = TPS.get(nom_tp, {})
    composants_tp = tp.get("composants", [])
    if not composants_tp:
        return

    # Une sélection de TP repart toujours d'un canevas propre. On conserve l'ordre
    # pédagogique défini dans TPS pour obtenir une disposition stable.
    for nom in composants_tp:
        ajouter_composant_graphique(nom, marque=marque)

    st.session_state.bornes_par_arete = {}
    st.session_state.couleurs_fils_par_arete = {}
    st.session_state.pop("dernier_resultat_graphique", None)


def construire_circuit_reference_enseignant(nom_tp, marque="Schneider Electric"):
    """Construit le canevas de référence pré-câblé, réservé à l'enseignant."""
    if not STREAMLIT_FLOW_DISPONIBLE:
        return None, {}
    # Sauvegarde le canevas étudiant : le corrigé enseignant ne doit jamais
    # remplacer ni révéler les fils dans l'éditeur utilisé par les étudiants.
    ancien_circuit = st.session_state.get("circuit_graphique")
    anciennes_bornes = st.session_state.get("bornes_par_arete", {})
    anciennes_couleurs = st.session_state.get("couleurs_fils_par_arete", {})
    state = StreamlitFlowState(nodes=[], edges=[])
    st.session_state.circuit_graphique = state
    st.session_state.bornes_par_arete = {}
    st.session_state.couleurs_fils_par_arete = {}
    charger_composants_du_tp_graphique(nom_tp, marque=marque)
    state = st.session_state.circuit_graphique
    bornes_reference = dict(st.session_state.bornes_par_arete)
    couleurs_reference = dict(st.session_state.couleurs_fils_par_arete)
    st.session_state.circuit_graphique = ancien_circuit
    st.session_state.bornes_par_arete = anciennes_bornes
    st.session_state.couleurs_fils_par_arete = anciennes_couleurs

    # Indexe chaque broche par le nom du composant et le nom de la borne.
    index_broches = {}
    for node in state.nodes:
        data = node.data or {}
        if data.get("node_role") == "borne":
            index_broches[(data.get("component"), data.get("terminal"))] = node.id
        elif data.get("node_role") == "composant":
            # Le canevas enseignant est consultatif : aucun déplacement/suppression.
            try:
                node.draggable = False
                node.deletable = False
            except Exception:
                pass
    for liaison in TPS[nom_tp].get("liaisons", []):
        try:
            gauche, droite = liaison
            comp_a, borne_a = gauche.rsplit(".", 1)
            comp_b, borne_b = droite.rsplit(".", 1)
            source = index_broches.get((comp_a, borne_a))
            target = index_broches.get((comp_b, borne_b))
            if not source or not target:
                continue
            edge_id = f"ref_{uuid4().hex[:12]}"
            state.edges.append(StreamlitFlowEdge(
                id=edge_id, source=source, target=target,
                animated=False, label="", style={"stroke": "#16A34A", "strokeWidth": 3},
            ))
            st.session_state.bornes_par_arete[edge_id] = (borne_a, borne_b)
            st.session_state.couleurs_fils_par_arete[edge_id] = _couleur_initiale_fil(borne_a, borne_b)
        except Exception:
            # Une liaison mal définie dans TPS ne doit pas faire planter l'espace enseignant.
            continue
    return state, bornes_reference


def obtenir_mot_de_passe_enseignant():
    """Lit le secret depuis Streamlit Secrets ou la variable d'environnement."""
    try:
        valeur = st.secrets.get("mot_de_passe_enseignant", "")
        if valeur:
            return str(valeur)
    except Exception:
        pass
    return os.environ.get("LAB_ENSEIGNANT_PASSWORD", "")


def ajouter_composant_graphique(nom_composant, marque="Schneider Electric"):
    state = st.session_state.circuit_graphique
    bornes = next((elements[nom_composant] for elements in COMPOSANTS.values()
                   if nom_composant in elements), [])
    if not bornes:
        st.error("Composant introuvable dans la bibliothèque.")
        return
    node_id = f"cmp_{uuid4().hex[:10]}"
    numero = 1 + sum(1 for n in state.nodes if n.data.get("node_role") == "composant" and n.data.get("component") == nom_composant)
    instance = f"{nom_composant} #{numero}"
    # Disposition en grille : la carte est à gauche, ses broches individuelles à droite.
    nb_composants = sum(1 for n in state.nodes if n.data.get("node_role") == "composant")
    x0 = 80 + (nb_composants % 2) * 650
    y0 = 60 + (nb_composants // 2) * 620
    # Intégrer la photographie dans la carte React Flow elle-même (data URI),
    # afin qu'elle reste visible dans le canevas sans dépendre d'une URL externe.
    fiche = fiche_composant(nom_composant, "", bornes, marque)
    chemin_photo = fiche.get("photo")
    image_html = (
        "<div style='height:132px;display:flex;align-items:center;justify-content:center;"
        "background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;margin:7px 0;overflow:hidden'>"
        "<span style='font-size:12px;color:#64748b'>Photographie non disponible</span></div>"
    )
    if chemin_photo and chemin_photo.is_file():
        try:
            mime = mimetypes.guess_type(str(chemin_photo))[0] or "image/jpeg"
            encoded = base64.b64encode(chemin_photo.read_bytes()).decode("ascii")
            image_html = (
                "<div style='height:145px;display:flex;align-items:center;justify-content:center;"
                "background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;margin:7px 0;overflow:hidden'>"
                f"<img src='data:{mime};base64,{encoded}' alt='{html_escape(nom_composant)}' "
                "style='max-width:100%;max-height:140px;object-fit:contain;display:block'/>"
                "</div>"
            )
        except Exception:
            pass
    contenu = (
        f"<div style='padding:9px;min-width:250px;max-width:285px;font-family:Arial,sans-serif'>"
        f"<div style='font-weight:700;font-size:14px;color:#0f172a'>⚡ {html_escape(instance)}</div>"
        f"<div style='font-size:10px;color:#64748b;margin-top:2px'>{html_escape(marque)}</div>"
        f"{image_html}"
        f"<div style='font-size:12px;color:#1d4ed8;margin-top:4px'>Symbole : {html_escape(SYMBOLES_ELECTRIQUES.get(nom_composant, nom_composant))}</div>"
        f"<div style='font-size:10px;color:#475569;margin-top:6px;font-weight:700'>BORNES DISPONIBLES — relier les broches bleues</div>"
        f"<div style='font-size:10px;color:#334155;margin-top:3px'>{html_escape(' • '.join(bornes))}</div></div>"
    )
    card = StreamlitFlowNode(
        id=node_id, pos=(x0, y0), data={"content": contenu, "component": nom_composant,
        "instance": instance, "terminals": bornes, "node_role": "composant"},
        node_type="default", source_position="right", target_position="left",
        draggable=True, connectable=False, deletable=True, selectable=True,
        style={"width": "305px", "border": "1px solid #60a5fa", "borderRadius": "10px",
               "background": "#ffffff", "padding": "0px", "boxShadow": "0 2px 8px rgba(15,23,42,.10)"},
    )
    state.nodes.append(card)
    # Chaque broche est un vrai nœud React Flow indépendant, donc chaque fil part
    # précisément de la borne sélectionnée sur le canevas.
    for i, borne in enumerate(bornes):
        pin_id = f"pin_{uuid4().hex[:10]}"
        pin_html = (
            f"<div style='padding:5px 8px;min-width:112px;text-align:center;background:#eff6ff;"
            f"border:1px solid #2563eb;border-radius:7px;color:#12356b;font-size:12px;font-weight:700'>"
            f"● {html_escape(borne)}</div>"
        )
        pin = StreamlitFlowNode(
            id=pin_id, pos=(x0 + 340, y0 + i * 54),
            data={"content": pin_html, "component": nom_composant, "instance": instance,
                  "terminal": borne, "component_id": node_id, "node_role": "borne", "terminals": [borne]},
            node_type="default", source_position="right", target_position="left",
            draggable=True, connectable=True, deletable=True, selectable=True,
            style={"width": "125px", "minWidth": "125px", "border": "0px", "background": "transparent", "padding": "0px"},
        )
        state.nodes.append(pin)
    st.session_state.circuit_graphique = state



# ---------------------------------------------------------------------
# CÂBLAGE INDUSTRIEL : CONVENTIONS DE COULEURS ET SCHÉMA COLORÉ
# Les couleurs sont pédagogiques et doivent être adaptées au règlement
# de câblage et à la norme adoptés dans l'établissement.
# ---------------------------------------------------------------------
COULEURS_FILS = {
    "Phase L1/L2/L3 — noir": {"hex": "#202124", "type": "phase"},
    "Phase — marron": {"hex": "#8B4513", "type": "phase"},
    "Neutre N — bleu clair": {"hex": "#168BCE", "type": "neutre"},
    "Commande CA — rouge": {"hex": "#E53935", "type": "commande"},
    "+24 V CC — rouge": {"hex": "#E53935", "type": "positif"},
    "0 V CC / négatif — bleu": {"hex": "#1976D2", "type": "negatif"},
    "Conducteur de protection PE — vert/jaune": {"hex": "#159447", "type": "terre"},
    "Commande / signal — orange": {"hex": "#F28C28", "type": "signal"},
    "Autre conducteur — jaune": {"hex": "#E0B400", "type": "autre"},
}


def _couleur_initiale_fil(borne_a, borne_b):
    texte = f"{borne_a} {borne_b}".upper()
    if "PE" in texte or "TERRE" in texte:
        return "Conducteur de protection PE — vert/jaune"
    if any(x in texte for x in ("A1", "A2", "13", "14", "95", "96", "11", "12")):
        return "Commande CA — rouge"
    if "+24V" in texte or "5V" in texte or "3V3" in texte or "DC+" in texte:
        return "+24 V CC — rouge"
    if "0V" in texte or "GND" in texte or "DC-" in texte:
        return "0 V CC / négatif — bleu"
    if any(x in texte for x in ("L1", "L2", "L3", "T1", "T2", "T3")):
        return "Phase L1/L2/L3 — noir"
    if ".N" in texte or " N " in f" {texte} ":
        return "Neutre N — bleu clair"
    return "Autre conducteur — jaune"


def afficher_schema_cablage_colorie(state, bornes_par_arete, couleurs_par_arete):
    """Dessine les liaisons en reliant visuellement les composants via leurs broches."""
    fig = go.Figure()
    nodes = {n.id: n for n in state.nodes}
    composants = [n for n in state.nodes if n.data.get("node_role") == "composant"]
    if not composants:
        st.info("Ajoutez des composants pour afficher le schéma de câblage coloré.")
        return
    positions = {}
    for node in state.nodes:
        pos = getattr(node, "pos", getattr(node, "position", (0, 0)))
        try:
            if isinstance(pos, dict): x, y = float(pos.get("x", 0)), float(pos.get("y", 0))
            else: x, y = float(pos[0]), float(pos[1])
        except Exception: x, y = 0.0, 0.0
        positions[node.id] = (x, y)
    for edge in state.edges:
        info = _infos_borne_arete(state, edge)
        if not info: continue
        ca, ba, cb, bb = info
        na, nb = nodes.get(ca), nodes.get(cb)
        if not na or not nb: continue
        x1, y1 = positions.get(ca, (0, 0)); x2, y2 = positions.get(cb, (0, 0))
        label = couleurs_par_arete.get(edge.id) or _couleur_initiale_fil(ba or "", bb or "")
        config = COULEURS_FILS.get(label, COULEURS_FILS["Autre conducteur — jaune"])
        hover = f"{na.data.get('instance')}.{ba} ↔ {nb.data.get('instance')}.{bb}"
        fig.add_trace(go.Scatter(x=[x1, (x1+x2)/2, x2], y=[y1, (y1+y2)/2, y2], mode="lines",
            line=dict(color=config["hex"], width=5), name=label, hovertemplate=f"{html_escape(hover)}<br>{html_escape(label)}<extra></extra>"))
    fig.add_trace(go.Scatter(
        x=[positions[n.id][0] for n in composants], y=[positions[n.id][1] for n in composants],
        mode="markers+text", text=[n.data.get("instance", n.data.get("component", n.id)) for n in composants],
        textposition="top center", marker=dict(symbol="square", size=28, color="#E8F1FA", line=dict(color="#1D4ED8", width=2)),
        name="Appareils", hovertext=["Bornes : " + ", ".join(n.data.get("terminals", [])) for n in composants],
        hovertemplate="%{text}<br>%{hovertext}<extra></extra>"))
    fig.update_layout(title="Schéma de câblage — fils reliés aux broches", height=500,
        xaxis=dict(visible=False), yaxis=dict(visible=False, autorange="reversed"),
        showlegend=True, legend=dict(orientation="h", y=-0.15),
        margin=dict(l=20, r=20, t=55, b=65), plot_bgcolor="#FAFCFF", paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True, key="schema_cablage_colorie")


def analyser_circuit_graphique(tp_nom, state, bornes_par_arete):
    reference = TPS[tp_nom]
    nodes = {n.id: n for n in state.nodes}
    composants_presents = {
        n.data.get("component") for n in state.nodes
        if getattr(n, "data", None) and n.data.get("node_role") == "composant"
    }
    attendus_composants = set(reference["composants"])
    manquants = sorted(attendus_composants - composants_presents)
    supplementaires = sorted(composants_presents - attendus_composants)

    liaisons_reelles = set()
    aretes_sans_bornes = []
    for edge in state.edges:
        choix = bornes_par_arete.get(edge.id)
        if not choix:
            aretes_sans_bornes.append(edge.id)
            continue
        info = _infos_borne_arete(state, edge)
        if not info:
            continue
        comp_a, borne_a, comp_b, borne_b = info
        n1, n2 = nodes.get(comp_a), nodes.get(comp_b)
        if n1 is None or n2 is None or not borne_a or not borne_b:
            continue
        liaisons_reelles.add(normaliser_liaison(
            f"{n1.data.get('component')}.{borne_a}",
            f"{n2.data.get('component')}.{borne_b}"
        ))

    liaisons_attendues = {normaliser_liaison(a, b) for a, b in reference["liaisons"]}
    liaisons_manquantes = sorted(liaisons_attendues - liaisons_reelles)
    liaisons_incorrectes = sorted(liaisons_reelles - liaisons_attendues)
    nb_erreurs = len(manquants) + len(liaisons_manquantes) + len(liaisons_incorrectes) + len(aretes_sans_bornes)
    total = max(1, len(attendus_composants) + len(liaisons_attendues))
    note = 20.0 if nb_erreurs == 0 else round(max(0, 20 * (1 - nb_erreurs / total)), 2)

    details = []
    for c in manquants:
        details.append({"Type": "Composant manquant", "Élément": c, "Correction": "Ajouter le composant"})
    for c in supplementaires:
        details.append({"Type": "Composant supplémentaire", "Élément": c, "Correction": "Vérifier sa nécessité"})
    for a, b in liaisons_manquantes:
        details.append({"Type": "Liaison manquante", "Élément": f"{a} ↔ {b}", "Correction": "Relier ces deux bornes"})
    for a, b in liaisons_incorrectes:
        details.append({"Type": "Liaison incorrecte", "Élément": f"{a} ↔ {b}", "Correction": "Vérifier les bornes utilisées"})
    for edge_id in aretes_sans_bornes:
        details.append({"Type": "Bornes non définies", "Élément": edge_id, "Correction": "Choisir les bornes du fil"})

    return {"correct": nb_erreurs == 0, "note": note, "details": details}


# ---------------------------------------------------------------------
# SOLVEUR DC : ANALYSE NODALE MODIFIÉE (MNA)
# Modèles permanents : R, sources, diodes à seuil, bobines, enroulements moteurs
# simplifiés et contacts commutés. Les fils idéaux fusionnent les broches connectées.
# ---------------------------------------------------------------------
def resoudre_circuit_dc(state, bornes_par_arete, parametres, noeud_masse):
    """Solveur MNA DC permanent : R, sources, bobines, moteurs simplifiés, contacts et diodes idéalisées.

    Condensateur : circuit ouvert en régime permanent DC.
    Inductance : court-circuit idéal en régime permanent DC (sa résistance série peut être renseignée).
    Moteur : trois enroulements résistifs indépendants ; pas de FEM de rotation ni de dynamique mécanique.
    Diode : modèle à seuil constant (0,7 V par défaut), commutation itérative.
    """
    nodes = {n.id: n for n in state.nodes}
    composants = {n.id: n for n in state.nodes if n.data.get("node_role") == "composant"}
    parent = {}
    def find(x):
        parent.setdefault(x, x)
        if parent[x] != x: parent[x] = find(parent[x])
        return parent[x]
    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb: parent[rb] = ra
    def term(cid, borne): return f"{cid}::{borne}"

    for cid, node in composants.items():
        for borne in node.data.get("terminals", []): find(term(cid, borne))
    for edge in state.edges:
        info = _infos_borne_arete(state, edge)
        if info:
            ca, ba, cb, bb = info
            if ca in composants and cb in composants and ba and bb:
                union(term(ca, ba), term(cb, bb))

    # Les liaisons internes des composants idéalisés sont des courts-circuits fermés.
    for cid, node in composants.items():
        typ = node.data.get("component")
        par = parametres.get(cid, {})
        if typ == "Bobine" and par.get("modele_bobine", "résistance DC") == "inductance idéale (court-circuit DC)":
            union(term(cid, "A"), term(cid, "B"))
        if typ == "Contacteur KM1" and par.get("contacts_fermes", False):
            for a, b in (("L1", "T1"), ("L2", "T2"), ("L3", "T3"), ("13", "14")):
                if a in node.data.get("terminals", []) and b in node.data.get("terminals", []): union(term(cid,a), term(cid,b))
        if typ == "Relais auxiliaire" and par.get("contacts_no_fermes", False):
            for a,b in (("13","14"),("21","22")):
                if a in node.data.get("terminals", []) and b in node.data.get("terminals", []): union(term(cid,a), term(cid,b))
        if typ == "Relais thermique" and par.get("contact_95_96_ferme", True):
            if "95" in node.data.get("terminals", []) and "96" in node.data.get("terminals", []): union(term(cid,"95"), term(cid,"96"))
        if typ in ("Bouton poussoir NO", "Arrêt d'urgence NF", "Bouton poussoir NF", "Fusible", "Disjoncteur tripolaire"):
            ferme = bool(par.get("ferme", typ in ("Arrêt d'urgence NF", "Bouton poussoir NF", "Fusible")))
            bornes = node.data.get("terminals", [])
            if ferme:
                if typ == "Disjoncteur tripolaire":
                    for a,b in (("L1","T1"),("L2","T2"),("L3","T3")):
                        if a in bornes and b in bornes: union(term(cid,a),term(cid,b))
                elif len(bornes)>=2: union(term(cid,bornes[0]),term(cid,bornes[1]))

    roots, terminal_net = {}, {}
    for cid,node in composants.items():
        for borne in node.data.get("terminals", []):
            r=find(term(cid,borne)); roots.setdefault(r,f"N{len(roots)+1}")
            terminal_net[(cid,borne)] = roots[r]

    branches=[]; voltage_sources=[]; diodes=[]; passive_open=[]
    def add_r(cid, label, a, b, resistance, kind):
        if a not in node_terms(cid) or b not in node_terms(cid): return
        na,nb=terminal_net[(cid,a)],terminal_net[(cid,b)]
        if na==nb: raise ValueError(f"{label} est court-circuité.")
        if resistance <= 0: raise ValueError(f"La résistance de {label} doit être positive.")
        branches.append({"id":cid,"nom":label,"type":kind,"a":na,"b":nb,"R":float(resistance)})
    def node_terms(cid): return composants[cid].data.get("terminals", [])

    for cid,node in composants.items():
        typ=node.data.get("component"); ident=node.data.get("instance",typ); par=parametres.get(cid,{})
        bornes=node.data.get("terminals",[])
        if typ in ("Résistance","Résistance de puissance"):
            add_r(cid,ident,bornes[0],bornes[1],float(par.get("value",100.0)),"Résistance")
        elif typ == "Source de tension DC":
            voltage_sources.append({"id":cid,"nom":ident,"type":typ,"a":terminal_net[(cid,bornes[0])],"b":terminal_net[(cid,bornes[1])],"value":float(par.get("value",12.0))})
        elif typ == "Source de courant DC":
            branches.append({"id":cid,"nom":ident,"type":typ,"a":terminal_net[(cid,bornes[0])],"b":terminal_net[(cid,bornes[1])],"I":float(par.get("value",0.1))})
        elif typ == "Bobine":
            if par.get("modele_bobine", "résistance DC") == "inductance idéale (court-circuit DC)":
                passive_open.append({"id":cid,"nom":ident,"type":"Bobine (court-circuit DC)","a":terminal_net[(cid,"A")],"b":terminal_net[(cid,"B")]})
            else: add_r(cid,ident,"A","B",float(par.get("value",20.0)),"Bobine — résistance cuivre")
        elif typ == "Moteur asynchrone triphasé":
            rphase=float(par.get("value",12.0))
            for a,b in (("U1","U2"),("V1","V2"),("W1","W2")):
                add_r(cid,f"{ident} — enroulement {a[0]}",a,b,rphase,"Enroulement moteur (modèle R DC)")
        elif typ == "Diode de puissance":
            diodes.append({"id":cid,"nom":ident,"a":terminal_net[(cid,"Anode")],"b":terminal_net[(cid,"Cathode")],"vf":float(par.get("vf",0.7)),"on":False})
        elif typ == "Condensateur":
            passive_open.append({"id":cid,"nom":ident,"type":"Condensateur (ouvert en DC permanent)","a":terminal_net[(cid,"A")],"b":terminal_net[(cid,"B")]})
        elif typ == "Contacteur KM1":
            # Bobine du contacteur : résistance cuivre équivalente entre A1 et A2.
            add_r(cid, f"{ident} — bobine A1/A2", "A1", "A2", float(par.get("coil_r",1000.0)), "Bobine de contacteur")

    # Ne garder que les nœuds participant au réseau conducteur, pour ne pas rendre
    # singulier un condensateur isolé en circuit ouvert.
    active_nets=set()
    for e in branches+voltage_sources+diodes:
        active_nets.update((e["a"],e["b"]))
    nets=sorted(active_nets)
    if noeud_masse not in nets: raise ValueError("La masse choisie n'appartient pas au réseau simulable. Connectez-la à une source ou à une charge.")
    if not (branches or voltage_sources or diodes): raise ValueError("Aucun composant conducteur simulable n'est raccordé. Un condensateur seul est ouvert en régime permanent DC.")

    def solve_once():
        unknown=[n for n in nets if n!=noeud_masse]; idx={n:i for i,n in enumerate(unknown)}
        active=[d for d in diodes if d["on"]]
        vs=voltage_sources + [{"id":d["id"],"nom":d["nom"],"type":"Diode (seuil direct)","a":d["a"],"b":d["b"],"value":d["vf"]} for d in active]
        size=len(unknown)+len(vs); mat=np.zeros((size,size)); rhs=np.zeros(size)
        def stamp_g(a,b,g):
            if a!=noeud_masse: mat[idx[a],idx[a]]+=g
            if b!=noeud_masse: mat[idx[b],idx[b]]+=g
            if a!=noeud_masse and b!=noeud_masse:
                ia,ib=idx[a],idx[b]; mat[ia,ib]-=g; mat[ib,ia]-=g
        for d in diodes:
            if not d["on"]:
                # Résistance de fuite très élevée : évite une matrice singulière
                # lorsqu'une diode bloquée isole un nœud du réseau.
                stamp_g(d["a"], d["b"], 1e-9)
        for e in branches:
            if e["type"]=="Source de courant DC":
                if e["a"]!=noeud_masse: rhs[idx[e["a"]]]-=e["I"]
                if e["b"]!=noeud_masse: rhs[idx[e["b"]]]+=e["I"]
            else: stamp_g(e["a"],e["b"],1.0/e["R"])
        for k,e in enumerate(vs):
            row=len(unknown)+k; a,b=e["a"],e["b"]
            if a!=noeud_masse: mat[idx[a],row]+=1; mat[row,idx[a]]+=1
            if b!=noeud_masse: mat[idx[b],row]-=1; mat[row,idx[b]]-=1
            rhs[row]=e["value"]
        try: sol=np.linalg.solve(mat,rhs)
        except np.linalg.LinAlgError as exc: raise ValueError("Réseau singulier : nœud flottant, circuit ouvert ou sources idéales incompatibles. Vérifiez les connexions et la masse.") from exc
        volts={noeud_masse:0.0}; volts.update({n:float(sol[i]) for n,i in idx.items()})
        currents={e["id"]:float(sol[len(unknown)+k]) for k,e in enumerate(vs)}
        return volts,currents

    for _ in range(20):
        volts, currents_vs=solve_once(); changed=False
        for d in diodes:
            vd=volts.get(d["a"],0.0)-volts.get(d["b"],0.0)
            current=currents_vs.get(d["id"],0.0)
            new_on=(vd >= d["vf"]-1e-7) if not d["on"] else (current >= -1e-8)
            if new_on != d["on"]: d["on"]=new_on; changed=True
        if not changed: break
    volts, currents_vs=solve_once()

    rows=[]
    for e in branches:
        va,vb=volts.get(e["a"],0.0),volts.get(e["b"],0.0)
        if e["type"]=="Source de courant DC": i=e["I"]; typ=e["type"]
        else: i=(va-vb)/e["R"]; typ=e["type"]
        rows.append({"Composant":e["nom"],"Modèle":typ,"Nœud +":e["a"],"Nœud -":e["b"],"Tension (V)":va-vb,"Courant (+ vers -) (A)":i,"Puissance absorbée (W)":(va-vb)*i})
    for e in voltage_sources:
        va,vb=volts.get(e["a"],0.0),volts.get(e["b"],0.0); i=currents_vs.get(e["id"],0.0)
        rows.append({"Composant":e["nom"],"Modèle":e["type"],"Nœud +":e["a"],"Nœud -":e["b"],"Tension (V)":va-vb,"Courant (+ vers -) (A)":i,"Puissance absorbée (W)":(va-vb)*i})
    for d in diodes:
        va,vb=volts.get(d["a"],0.0),volts.get(d["b"],0.0); i=currents_vs.get(d["id"],0.0) if d["on"] else 0.0
        rows.append({"Composant":d["nom"],"Modèle":"Diode passante" if d["on"] else "Diode bloquée","Nœud +":d["a"],"Nœud -":d["b"],"Tension (V)":va-vb,"Courant (+ vers -) (A)":i,"Puissance absorbée (W)":(va-vb)*i})
    for e in passive_open:
        va,vb=volts.get(e["a"],float("nan")),volts.get(e["b"],float("nan"))
        rows.append({"Composant":e["nom"],"Modèle":e["type"],"Nœud +":e["a"],"Nœud -":e["b"],"Tension (V)":va-vb if np.isfinite(va) and np.isfinite(vb) else float("nan"),"Courant (+ vers -) (A)":0.0,"Puissance absorbée (W)":0.0})
    return volts, pd.DataFrame(rows)



def creer_schema_tp(tp_nom):
    """Dessine un aperçu pédagogique du schéma de référence du TP."""
    tp = TPS[tp_nom]
    composants = tp["composants"]
    if not composants:
        return go.Figure()
    n = len(composants)
    angles = np.linspace(0, 2 * np.pi, n, endpoint=False)
    positions = {
        nom: (float(np.cos(a)), float(np.sin(a)))
        for nom, a in zip(composants, angles)
    }
    fig = go.Figure()
    for a, b in tp["liaisons"]:
        ca, ba = a.rsplit(".", 1)
        cb, bb = b.rsplit(".", 1)
        if ca not in positions or cb not in positions:
            continue
        xa, ya = positions[ca]
        xb, yb = positions[cb]
        fig.add_trace(go.Scatter(
            x=[xa, xb], y=[ya, yb], mode="lines",
            line=dict(color="#16a34a", width=2),
            hovertemplate=f"{ca}.{ba} ↔ {cb}.{bb}<extra>Connexion de référence</extra>",
            showlegend=False,
        ))
        xm, ym = (xa + xb) / 2, (ya + yb) / 2
        fig.add_annotation(x=xm, y=ym, text=f"{ba} ↔ {bb}", showarrow=False,
                           font=dict(size=9, color="#166534"), bgcolor="rgba(255,255,255,.85)")
    for nom, (x, y) in positions.items():
        fig.add_trace(go.Scatter(
            x=[x], y=[y], mode="markers+text", text=[nom], textposition="bottom center",
            marker=dict(size=34, color="#dbeafe", line=dict(color="#1d4ed8", width=2)),
            textfont=dict(size=10, color="#0f172a"),
            hovertemplate=f"<b>{nom}</b><extra>Composant du TP</extra>", showlegend=False,
        ))
    fig.update_layout(
        title=f"Schéma de référence — {tp_nom}", height=520,
        xaxis=dict(visible=False, range=[-1.5, 1.5]),
        yaxis=dict(visible=False, range=[-1.45, 1.45], scaleanchor="x", scaleratio=1),
        margin=dict(l=20, r=20, t=55, b=20),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def tracer_courbe_sonde(tp_nom, type_mesure, borne_a, borne_b, composant_courant):
    """Produit une courbe pédagogique illustrative selon le TP choisi."""
    fig = go.Figure()
    if tp_nom == "Redressement monophasé - Pont de Graetz":
        u = float(st.session_state.get("gr_u", 24.0))
        f = float(st.session_state.get("gr_f", 50.0))
        vd = float(st.session_state.get("gr_vd", 0.7))
        t = np.linspace(0, 2 / f, 1200)
        signal = u * np.sqrt(2) * np.sin(2 * np.pi * f * t)
        if "Courant" in type_mesure:
            r = float(st.session_state.get("gr_r", 100.0))
            y = np.maximum(np.abs(signal) - 2 * vd, 0) / r
            unite, titre = "A", "Courant de charge redressé"
        else:
            y = np.maximum(np.abs(signal) - 2 * vd, 0)
            unite, titre = "V", "Tension redressée"
        fig.add_trace(go.Scatter(x=t, y=y, name=titre))
        axe = "Temps (s)"
    elif tp_nom == "Mesure des caractéristiques d'un circuit RC":
        r = float(st.session_state.get("rc_r", 1000.0))
        c = float(st.session_state.get("rc_c", 100.0)) * 1e-6
        u = float(st.session_state.get("rc_v", 5.0))
        tau = r * c
        t = np.linspace(0, 5 * tau, 700)
        charge = u * (1 - np.exp(-t / tau))
        if "Courant" in type_mesure:
            y = (u / r) * np.exp(-t / tau)
            unite, titre = "A", "Courant de charge RC"
        else:
            y = charge
            unite, titre = "V", "Tension du condensateur"
        fig.add_trace(go.Scatter(x=t, y=y, name=titre))
        axe = "Temps (s)"
    elif tp_nom == "Démarrage direct d'un moteur asynchrone":
        i0 = float(st.session_state.get("mot_istart", 6.0))
        t = np.linspace(0, 2, 500)
        if "Courant" in type_mesure:
            y = 6 * np.exp(-t / 0.22) + 1
            unite, titre = "× In", "Enveloppe indicative du courant de démarrage"
        else:
            y = np.sin(2 * np.pi * 50 * t) * (1 + (i0 - 1) * np.exp(-t / 0.22))
            unite, titre = "V (normalisé)", "Tension illustrative avec enveloppe transitoire"
        fig.add_trace(go.Scatter(x=t, y=y, name=titre))
        axe = "Temps (s)"
    else:
        t = np.linspace(0, 0.1, 500)
        y = 5 * np.sin(2 * np.pi * 50 * t)
        fig.add_trace(go.Scatter(x=t, y=y, name="Signal de commande illustratif"))
        unite, axe, titre = "V", "Temps (s)", "Signal de commande"
    fig.update_layout(
        title=f"{titre} — sonde : {borne_a} / {borne_b}" if "Tension" in type_mesure else f"{titre} — {composant_courant}",
        xaxis_title=axe, yaxis_title=unite, height=360,
        legend=dict(orientation="h"), margin=dict(t=55, b=35),
    )
    return fig

# ---------------------------------------------------------------------
# PAGES
# ---------------------------------------------------------------------
if espace == "🏠 Accueil":
    st.title("⚡ Bienvenue au laboratoire virtuel")
    st.write(
        "Cette plateforme accompagne les étudiants dans la préparation, "
        "le câblage logique et l'analyse de travaux pratiques en électrotechnique."
    )
    c1, c2, c3 = st.columns(3)
    c1.metric("Travaux pratiques", len(TPS))
    c2.metric("Catégories de composants", len(COMPOSANTS))
    c3.metric("Composants disponibles", sum(len(v) for v in COMPOSANTS.values()))
    st.subheader("Parcours de l'étudiant")
    st.markdown(
        """
        1. Renseigner votre identité et votre groupe dans la barre latérale.
        2. Choisir un TP dans **Réaliser un TP**.
        3. Sélectionner les composants et effectuer les liaisons.
        4. Cliquer sur **Vérifier et corriger mon montage**.
        5. Importer vos mesures dans **Mesures réelles & comparaison**.
        """
    )
    st.info(
        "Les corrigés présents dans cette version sont des exemples pédagogiques. "
        "L'enseignant devra les vérifier et les adapter aux schémas officiels du laboratoire."
    )

elif espace == "🧰 Bibliothèque de composants":
    st.title("🧰 Bibliothèque de composants électriques")
    st.write("Recherchez un composant, consultez son illustration générée par IA, son symbole électrique et sa fiche technique.")
    total_composants = sum(len(v) for v in COMPOSANTS.values())
    marque_bibliotheque = st.selectbox(
        "🏷️ Choisir la marque des composants",
        list(MARQUES_COMPOSANTS.keys()),
        key="marque_bibliotheque",
        help="La photographie affichée dépend de la marque sélectionnée. Les symboles électriques restent normalisés.",
    )
    st.caption("🖼️ Illustrations générées par IA : visuels pédagogiques pour reconnaître les familles d'appareils. Elles ne sont pas des photographies officielles ni des références commerciales exactes Schneider Electric, ABB ou Siemens.")
    nb_photos = sum(1 for cat, elements in COMPOSANTS.items() for nom, bornes in elements.items()
                    if fiche_composant(nom, cat, bornes, marque_bibliotheque)["photo"].is_file())
    m1, m2, m3 = st.columns(3)
    m1.metric("Composants référencés", total_composants)
    m2.metric("Catégories", len(COMPOSANTS))
    m3.metric("Illustrations IA installées", f"{nb_photos}/{total_composants}")
    recherche_bib = st.text_input("🔎 Rechercher par nom", placeholder="Ex. moteur, contacteur, diode, Arduino…", key="recherche_bibliotheque")
    categories_bib = ["Toutes les catégories"] + list(COMPOSANTS.keys())
    categorie_bib = st.selectbox("Catégorie", categories_bib, key="categorie_bibliotheque")
    liste_bib = []
    for cat, elements in COMPOSANTS.items():
        if categorie_bib != "Toutes les catégories" and cat != categorie_bib:
            continue
        for nom, bornes in elements.items():
            if recherche_bib.strip() and recherche_bib.casefold() not in nom.casefold() and recherche_bib.casefold() not in cat.casefold():
                continue
            liste_bib.append((cat, nom, bornes))
    st.caption(f"{len(liste_bib)} composant(s) correspondant(s).")
    if not liste_bib:
        st.warning("Aucun composant ne correspond à cette recherche.")
    for cat, nom, bornes in liste_bib:
        fiche = fiche_composant(nom, cat, bornes, marque_bibliotheque)
        with st.expander(f"⚡ {nom}  ·  {cat}", expanded=(len(liste_bib) == 1)):
            gauche, droite = st.columns([1.05, 1.4], gap="large")
            with gauche:
                afficher_photo_composant(nom, fiche)
                st.markdown("**Symbole électrique utilisé dans le schéma**")
                st.code(fiche["symbole"], language=None)
                st.caption("La photographie représente le matériel réel ; le symbole est une représentation conventionnelle pour le schéma.")
            with droite:
                st.markdown("**Désignation**")
                st.write(nom)
                st.markdown("**Fonction**")
                st.write(fiche["fonction"])
                st.markdown("**Bornes / raccordements**")
                st.write(fiche["bornes"])
                st.markdown("**Caractéristiques nominales**")
                st.write(fiche["caracteristiques"])
                st.markdown("**Utilisation**")
                st.write(fiche["utilisation"])
                st.caption("Les valeurs chiffrées doivent être relevées sur la plaque signalétique ou la fiche constructeur du modèle réellement utilisé.")
                if st.button("➕ Ajouter ce composant à l’éditeur", key=f"bib_add_{_slug_composant(nom)}", use_container_width=True):
                    if not STREAMLIT_FLOW_DISPONIBLE:
                        st.error("L'éditeur nécessite streamlit-flow-component==1.6.1.")
                    else:
                        initialiser_circuit_graphique()
                        ajouter_composant_graphique(nom)
                        st.success(f"{nom} ajouté au canevas. Ouvrez « Éditeur graphique de circuits » pour le câblage.")

elif espace == "🧩 Éditeur graphique de circuits":
    st.title("🧩 Atelier graphique de câblage électrique")
    st.write(
        "Reconnaissez les appareils, placez-les dans le canevas, reliez les bornes "
        "par glisser-déposer, choisissez la couleur de chaque conducteur et vérifiez "
        "votre câblage de puissance et de commande."
    )
    if not STREAMLIT_FLOW_DISPONIBLE:
        st.error("Module absent : ajoutez streamlit-flow-component==1.6.1 à requirements.txt.")
        st.stop()

    initialiser_circuit_graphique()
    # Le choix de marque est placé avant le chargement du TP pour que chaque
    # carte reçoive immédiatement la photographie correspondant à la marque.
    marque_graphique = st.selectbox("🏷️ Marque des composants", list(MARQUES_COMPOSANTS.keys()), key="marque_graphique")
    tp_graphique = st.selectbox("TP de référence", list(TPS.keys()), key="tp_graphique_select")
    if st.session_state.tp_graphique_courant != tp_graphique:
        st.session_state.tp_graphique_courant = tp_graphique
        st.session_state.circuit_graphique = StreamlitFlowState(nodes=[], edges=[])
        st.session_state.bornes_par_arete = {}
        st.session_state.couleurs_fils_par_arete = {}
        st.session_state.pop("dernier_resultat_graphique", None)
        # Dès le choix du TP, afficher tous les composants attendus dans la zone
        # graphique. Aucun fil n'est créé : l'étudiant réalise le montage.
        charger_composants_du_tp_graphique(tp_graphique, marque=marque_graphique)

    st.info(TPS[tp_graphique]["description"])
    col_bib, col_canvas = st.columns([1, 3], gap="large")
    with col_bib:
        st.subheader("🧰 Bibliothèque complémentaire")
        st.caption("Les photos des appareils du TP sont maintenant affichées directement sur leurs cartes dans le canevas. Les broches bleues restent les points de connexion.")
        categorie_graph = st.selectbox("Catégorie", list(COMPOSANTS.keys()), key="cat_graphique")
        recherche_graph = st.text_input("Rechercher un composant", key="recherche_composant_graph")
        choix_graph = [n for n in COMPOSANTS[categorie_graph] if recherche_graph.casefold() in n.casefold()]
        if not choix_graph:
            st.warning("Aucun composant trouvé dans cette catégorie.")
            choix_graph = list(COMPOSANTS[categorie_graph])
        composant_graph = st.selectbox("Composant", choix_graph, key="composant_graphique")
        fiche_graph = fiche_composant(composant_graph, categorie_graph, COMPOSANTS[categorie_graph][composant_graph], marque_graphique)
        afficher_photo_composant(composant_graph, fiche_graph)
        st.caption(f"Symbole : {fiche_graph['symbole']}")
        if st.button("➕ Placer dans le circuit", use_container_width=True):
            ajouter_composant_graphique(composant_graph, marque=marque_graphique)
            st.rerun()
        st.divider()
        st.caption("Composants chargés automatiquement pour ce TP")
        for item in TPS[tp_graphique]["composants"]:
            st.write(f"✓ {item}")
        st.caption("Tous ces appareils sont déjà placés dans le canevas. Vous pouvez les déplacer et réaliser vous-même chaque liaison.")
        if st.button("↻ Replacer les composants du TP", use_container_width=True, key="recharger_composants_tp_graphique"):
            st.session_state.circuit_graphique = StreamlitFlowState(nodes=[], edges=[])
            st.session_state.bornes_par_arete = {}
            st.session_state.couleurs_fils_par_arete = {}
            charger_composants_du_tp_graphique(tp_graphique, marque=marque_graphique)
            st.rerun()
        if st.button("🗑️ Réinitialiser le canevas", use_container_width=True):
            st.session_state.circuit_graphique = StreamlitFlowState(nodes=[], edges=[])
            st.session_state.bornes_par_arete = {}
            st.session_state.couleurs_fils_par_arete = {}
            st.session_state.pop("dernier_resultat_graphique", None)
            st.rerun()

    with col_canvas:
        st.subheader("⚙️ Zone de câblage")
        with st.expander("ℹ️ Configuration des nœuds", expanded=False):
            st.markdown(
                "- **Node Content** : nom de l'appareil, symbole et liste de ses bornes.\\n"
                "- **Node Width** : 230 px pour afficher correctement les informations.\\n"
                "- **Type** : `default` (entrée et sortie disponibles).\\n"
                "- **Source Position** : `Right` (sortie à droite).\\n"
                "- **Target Position** : `Left` (entrée à gauche).\\n"
                "- **Draggable / Connectable / Deletable** : activés.\\n\\n"
                "Chaque broche affichée est un nœud connectable distinct : le fil mémorise "
                "automatiquement l'identifiant de la borne de départ et celui de la borne d'arrivée."
            )
        st.caption(
            "Chaque carte affiche la photographie du composant, sa marque et ses bornes. "
            "Les bornes bleues sont des points de connexion indépendants : reliez une broche "
            "à une autre broche pour créer le conducteur. Les cartes et broches peuvent être déplacées séparément."
        )
        st.session_state.circuit_graphique = streamlit_flow(
            "atelier_electrique_graphique",
            st.session_state.circuit_graphique,
            height=590, fit_view=True, show_minimap=True,
            hide_watermark=True, allow_new_edges=True,
            enable_node_menu=True, enable_edge_menu=True, enable_pane_menu=True,
            get_node_on_click=True, get_edge_on_click=True, min_zoom=0.15,
        )

    state_graph = st.session_state.circuit_graphique
    edge_ids = {edge.id for edge in state_graph.edges}
    st.session_state.bornes_par_arete = {
        k: v for k, v in st.session_state.bornes_par_arete.items() if k in edge_ids
    }

    # Les bornes sont maintenant déterminées par les broches graphiques réellement reliées.
    st.session_state.bornes_par_arete = _paires_bornes_graphiques(state_graph)
    st.subheader("🔌 Connexions broche à broche")
    if not state_graph.nodes:
        st.warning("Le canevas est vide : placez les composants à gauche.")
    elif not state_graph.edges:
        st.info("Aucun fil : reliez directement deux broches bleues dans le canevas.")
    else:
        nodes_edge = {n.id: n for n in state_graph.nodes}
        for edge in state_graph.edges:
            info = _infos_borne_arete(state_graph, edge)
            if not info: continue
            ca, ba, cb, bb = info
            na, nb = nodes_edge.get(ca), nodes_edge.get(cb)
            if not na or not nb or not ba or not bb:
                st.warning("Ancienne liaison sans broches : supprimez-la et recréez le fil entre deux broches.")
                continue
            st.markdown(f"**{na.data.get('instance')}.{ba}  ↔  {nb.data.get('instance')}.{bb}**")
            choix = st.session_state.bornes_par_arete.get(edge.id, (ba, bb))
            couleur_defaut = st.session_state.couleurs_fils_par_arete.get(edge.id, _couleur_initiale_fil(*choix))
            options_couleur = list(COULEURS_FILS.keys())
            couleur = st.selectbox("Couleur / fonction du conducteur", options_couleur,
                index=options_couleur.index(couleur_defaut) if couleur_defaut in options_couleur else 0,
                key=f"wire_color_{edge.id}")
            st.session_state.couleurs_fils_par_arete[edge.id] = couleur
            st.divider()

    if state_graph.edges:
        st.subheader("🎨 Visualisation des conducteurs réels")
        st.caption("Les couleurs sont visibles sur ce schéma de câblage. Le conducteur PE est représenté en vert/jaune bicolore.")
        afficher_schema_cablage_colorie(
            state_graph, st.session_state.bornes_par_arete,
            st.session_state.couleurs_fils_par_arete
        )
    st.markdown(
        "**Repères de câblage :** phases en noir/marron, neutre en bleu, commande en rouge, "
        "conducteur de protection PE en vert/jaune. Les couleurs doivent toujours être "
        "confirmées avec la norme et les consignes de sécurité applicables au montage réel."
    )

    st.divider()
    st.header("🔬 Simulation du circuit réellement câblé — solveur DC")
    st.markdown(
        "Les connexions entre broches forment les nœuds électriques. Le solveur DC permanent "
        "calcule résistances, sources continues, diodes à seuil, bobines, enroulements moteurs "
        "simplifiés et bobines de contacteurs avec états de contacts configurables. Les condensateurs "
        "sont ouverts en régime permanent DC ; les phénomènes transitoires nécessitent une analyse temporelle."
    )
    supported_nodes = [
        n for n in state_graph.nodes if n.data.get("node_role") == "composant" and n.data.get("component") in (
            "Résistance", "Résistance de puissance", "Source de tension DC", "Source de courant DC",
            "Bobine", "Condensateur", "Diode de puissance", "Moteur asynchrone triphasé", "Contacteur KM1"
        )
    ]
    parametres_dc = {}
    if supported_nodes:
        st.subheader("Paramètres des composants simulés")
        for node in supported_nodes:
            typ = node.data.get("component")
            ident = node.data.get("instance", typ)
            parametres_dc[node.id] = {}
            if typ in ("Résistance", "Résistance de puissance"):
                parametres_dc[node.id]["value"] = st.number_input(f"{ident} — résistance (Ω)", min_value=0.000001, value=100.0, format="%.6g", key=f"dc_value_{node.id}")
            elif typ == "Source de tension DC":
                parametres_dc[node.id]["value"] = st.number_input(f"{ident} — tension (V)", value=12.0, format="%.6g", key=f"dc_value_{node.id}")
            elif typ == "Source de courant DC":
                parametres_dc[node.id]["value"] = st.number_input(f"{ident} — courant (A)", value=0.1, format="%.6g", key=f"dc_value_{node.id}")
            elif typ == "Bobine":
                parametres_dc[node.id]["modele_bobine"] = st.selectbox(f"{ident} — modèle DC", ["résistance DC", "inductance idéale (court-circuit DC)"], key=f"dc_bob_mode_{node.id}")
                if parametres_dc[node.id]["modele_bobine"] == "résistance DC": parametres_dc[node.id]["value"] = st.number_input(f"{ident} — résistance cuivre (Ω)", min_value=0.0001, value=20.0, key=f"dc_bob_r_{node.id}")
            elif typ == "Diode de puissance":
                parametres_dc[node.id]["vf"] = st.number_input(f"{ident} — seuil direct Vf (V)", min_value=0.1, max_value=2.0, value=0.7, step=0.05, key=f"dc_diode_{node.id}")
            elif typ == "Moteur asynchrone triphasé":
                parametres_dc[node.id]["value"] = st.number_input(f"{ident} — résistance par enroulement (Ω)", min_value=0.001, value=12.0, key=f"dc_motor_{node.id}")
            elif typ == "Contacteur KM1":
                parametres_dc[node.id]["coil_r"] = st.number_input(f"{ident} — résistance bobine A1/A2 (Ω)", min_value=1.0, value=1000.0, key=f"dc_coil_{node.id}")
                parametres_dc[node.id]["contacts_fermes"] = st.checkbox(f"{ident} — contacts de puissance et auxiliaire NO fermés", value=False, key=f"dc_contacts_{node.id}")

        # Reconstituer les réseaux électriques pour proposer un choix de masse
        # et des points de mesure qui correspondent aux fils réellement posés.
        parent_mesure = {}
        def find_mesure(x):
            parent_mesure.setdefault(x, x)
            if parent_mesure[x] != x:
                parent_mesure[x] = find_mesure(parent_mesure[x])
            return parent_mesure[x]
        def union_mesure(a, b):
            ra, rb = find_mesure(a), find_mesure(b)
            if ra != rb:
                parent_mesure[rb] = ra
        for node in state_graph.nodes:
            if node.data.get("node_role") != "composant": continue
            for terminal in node.data.get("terminals", []): find_mesure(f"{node.id}::{terminal}")
        for edge in state_graph.edges:
            info = _infos_borne_arete(state_graph, edge)
            if info:
                ca, ba, cb, bb = info
                if ca and cb and ba and bb: union_mesure(f"{ca}::{ba}", f"{cb}::{bb}")
        racines = {}
        terminal_vers_noeud = {}
        for node in state_graph.nodes:
            if node.data.get("node_role") != "composant": continue
            for terminal in node.data.get("terminals", []):
                cle = f"{node.id}::{terminal}"; racine = find_mesure(cle)
                racines.setdefault(racine, f"N{len(racines)+1}")
                terminal_vers_noeud[f"{node.data.get('instance', node.data.get('component'))}.{terminal}"] = racines[racine]
        noeuds_disponibles = sorted(set(terminal_vers_noeud.values()))
        labels_noeuds = {
            net: ", ".join(b for b, nnet in terminal_vers_noeud.items() if nnet == net)
            for net in noeuds_disponibles
        }
        masse = st.selectbox(
            "Nœud de référence (masse 0 V)", noeuds_disponibles,
            format_func=lambda net: f"{net} — {labels_noeuds.get(net, '')}",
            key=f"dc_ground_{tp_graphique}"
        )
        if st.button("⚡ Résoudre le circuit câblé", type="primary", key="resoudre_dc_graphique"):
            try:
                tensions_dc, tableau_dc = resoudre_circuit_dc(
                    state_graph, st.session_state.bornes_par_arete, parametres_dc, masse
                )
                st.session_state.resultat_solveur_dc = {
                    "tensions": tensions_dc, "tableau": tableau_dc,
                    "terminal_vers_noeud": terminal_vers_noeud,
                    "tp": tp_graphique,
                }
                st.success("Circuit résolu : les résultats proviennent des connexions du canevas.")
            except Exception as exc:
                st.session_state.resultat_solveur_dc = None
                st.error(f"Simulation impossible : {exc}")

        resultat_dc = st.session_state.get("resultat_solveur_dc")
        if resultat_dc and resultat_dc.get("tp") == tp_graphique:
            st.subheader("Résultats du solveur")
            lignes_tensions = [
                {"Nœud": net, "Tension par rapport à la masse (V)": round(val, 6)}
                for net, val in resultat_dc["tensions"].items()
            ]
            st.dataframe(pd.DataFrame(lignes_tensions), use_container_width=True, hide_index=True)
            st.dataframe(resultat_dc["tableau"].round(6), use_container_width=True, hide_index=True)

            st.subheader("Appareils de mesure virtuels")
            bornes_mesure = list(resultat_dc["terminal_vers_noeud"].keys())
            mesure_type = st.radio(
                "Instrument", ["Voltmètre", "Ampèremètre"], horizontal=True,
                key="instrument_virtuel_dc"
            )
            if mesure_type == "Voltmètre":
                vm1, vm2 = st.columns(2)
                with vm1:
                    point_plus = st.selectbox("Pointe rouge (+)", bornes_mesure, key="probe_plus_dc")
                with vm2:
                    point_moins = st.selectbox("Pointe noire (COM)", bornes_mesure, key="probe_minus_dc")
                nplus = resultat_dc["terminal_vers_noeud"][point_plus]
                nmoins = resultat_dc["terminal_vers_noeud"][point_moins]
                vmes = resultat_dc["tensions"].get(nplus, 0.0) - resultat_dc["tensions"].get(nmoins, 0.0)
                st.metric("Tension mesurée", f"{vmes:.6g} V", help="Différence de potentiel calculée entre les deux bornes choisies.")
            else:
                noms_elements = resultat_dc["tableau"]["Composant"].tolist()
                element_mesure = st.selectbox("Composant traversé", noms_elements, key="probe_current_dc")
                ligne_mesure = resultat_dc["tableau"].loc[resultat_dc["tableau"]["Composant"] == element_mesure].iloc[0]
                st.metric("Courant mesuré (+ vers -)", f"{ligne_mesure['Courant (+ vers -) (A)']:.6g} A")
                st.caption(f"Tension aux bornes : {ligne_mesure['Tension (V)']:.6g} V · Puissance : {ligne_mesure['Puissance absorbée (W)']:.6g} W")
    else:
        st.info("Ajoutez une source DC et au moins un composant conducteur pris en charge. Un condensateur seul est ouvert en régime permanent continu.")

    st.info(
        "Modèles actuellement disponibles : résistances, sources DC, diodes à seuil constant, "
        "bobines avec résistance cuivre ou inductance idéale en régime permanent, "
        "enroulements moteurs représentés par trois résistances, et bobines/contacts de contacteurs. "
        "Les condensateurs sont modélisés comme circuits ouverts en DC permanent. "
        "Les transitoires RC/RL, la commutation détaillée, le glissement et la FEM des moteurs "
        "nécessitent un solveur temporel spécialisé."
    )

    st.divider()
    st.header("⚡ Calculs électriques et simulation physique")
    st.caption(
        "Les modèles ci-dessous calculent des grandeurs électriques à partir des "
        "paramètres physiques saisis. Ils complètent le contrôle logique du câblage."
    )

    if tp_graphique == "Démarrage direct d'un moteur asynchrone":
        st.subheader("Moteur asynchrone triphasé — régime nominal")
        st.info(
            "Modèle triphasé équilibré en régime permanent. Les paramètres doivent "
            "être relevés sur la plaque signalétique du moteur ou fournis par l'enseignant."
        )
        m1, m2, m3 = st.columns(3)
        with m1:
            tension_ligne = st.number_input("Tension composée U (V)", 100.0, 1000.0, 400.0, 10.0, key="mot_u")
            puissance_meca_kw = st.number_input("Puissance utile P₂ (kW)", 0.05, 500.0, 4.0, 0.05, key="mot_p")
        with m2:
            rendement = st.number_input("Rendement η (%)", 10.0, 100.0, 86.0, 0.5, key="mot_eta") / 100
            facteur_puissance = st.number_input("Facteur de puissance cos φ", 0.1, 1.0, 0.82, 0.01, key="mot_cos")
        with m3:
            vitesse = st.number_input("Vitesse nominale n (tr/min)", 100.0, 6000.0, 1450.0, 10.0, key="mot_n")
            rapport_demarrage = st.number_input("Rapport I démarrage / I nominal", 1.0, 12.0, 6.0, 0.1, key="mot_istart")

        p2_w = puissance_meca_kw * 1000
        p1_w = p2_w / rendement
        s_va = p1_w / facteur_puissance
        q_var = math.sqrt(max(0.0, s_va**2 - p1_w**2))
        i_nom = s_va / (math.sqrt(3) * tension_ligne)
        i_dem = rapport_demarrage * i_nom
        couple = 9550 * puissance_meca_kw / (vitesse / 1.0)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Courant nominal", f"{i_nom:.2f} A")
        c2.metric("Courant de démarrage estimé", f"{i_dem:.2f} A")
        c3.metric("Puissance absorbée", f"{p1_w/1000:.2f} kW")
        c4.metric("Couple nominal", f"{couple:.2f} N·m")
        st.write(
            f"Puissance apparente : **{s_va/1000:.2f} kVA** · "
            f"Puissance réactive : **{q_var/1000:.2f} kvar** · "
            f"Pertes estimées : **{(p1_w-p2_w)/1000:.2f} kW**"
        )
        st.latex(r"P_1=\\frac{P_2}{\\eta},\\quad I_n=\\frac{P_1}{\\sqrt{3}\\,U\\cos\\varphi},\\quad T_n=\\frac{9550P_2(\\mathrm{kW})}{n(\\mathrm{tr/min})}")
        st.warning(
            "Le courant de démarrage affiché est une estimation par multiplicateur saisi. "
            "Ce modèle ne calcule pas le transitoire électromagnétique, le glissement, "
            "le couple de démarrage ni la saturation. Vérifiez aussi le couplage étoile/triangle "
            "selon la plaque moteur et la tension du réseau."
        )

    elif tp_graphique == "Redressement monophasé - Pont de Graetz":
        st.subheader("Pont de Graetz — charge résistive")
        r1, r2, r3 = st.columns(3)
        with r1:
            u_secondaire = st.number_input("Tension secondaire efficace (V)", 1.0, 500.0, 24.0, 1.0, key="gr_u")
            frequence = st.number_input("Fréquence (Hz)", 1.0, 400.0, 50.0, 1.0, key="gr_f")
        with r2:
            resistance_charge = st.number_input("Résistance de charge (Ω)", 0.1, 100000.0, 100.0, 1.0, key="gr_r")
            chute_diode = st.number_input("Chute directe par diode (V)", 0.0, 3.0, 0.7, 0.05, key="gr_vd")
        with r3:
            inductance_mh = st.number_input("Inductance série (mH, 0 = aucune)", 0.0, 10000.0, 0.0, 1.0, key="gr_l")

        vm = math.sqrt(2) * u_secondaire
        t = np.linspace(0, 2 / frequence, 2000)
        vs = vm * np.sin(2 * np.pi * frequence * t)
        vo = np.maximum(np.abs(vs) - 2 * chute_diode, 0)
        io = vo / resistance_charge
        u_moy = float(_np_integrale_trapezes(vo, t) / (t[-1] - t[0]))
        u_eff = float(math.sqrt(_np_integrale_trapezes(vo**2, t) / (t[-1] - t[0])))
        i_moy = u_moy / resistance_charge
        p_charge = u_eff**2 / resistance_charge
        ondulation = 2 * frequence

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Tension moyenne", f"{u_moy:.2f} V")
        c2.metric("Tension efficace", f"{u_eff:.2f} V")
        c3.metric("Courant moyen", f"{i_moy:.3f} A")
        c4.metric("Puissance charge", f"{p_charge:.2f} W")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=t, y=vs, name="Tension secondaire", line=dict(width=1.5)))
        fig.add_trace(go.Scatter(x=t, y=vo, name="Sortie redressée", line=dict(width=2)))
        fig.update_layout(
            title="Tension d'entrée et tension redressée",
            xaxis_title="Temps (s)", yaxis_title="Tension (V)",
            legend=dict(orientation="h"), height=390,
        )
        st.plotly_chart(fig, use_container_width=True)
        fig_i = go.Figure(go.Scatter(x=t, y=io, name="Courant de charge"))
        fig_i.update_layout(title="Courant dans la charge résistive", xaxis_title="Temps (s)", yaxis_title="Courant (A)", height=300)
        st.plotly_chart(fig_i, use_container_width=True)
        st.write(
            f"Fréquence d'ondulation : **{ondulation:.1f} Hz** · "
            f"Puissance dissipée : **{p_charge:.2f} W**"
        )
        st.caption(
            "Modèle de pont idéal avec deux diodes conductrices et chute directe constante. "
            "L'inductance saisie est informative dans cette version : le calcul temporel "
            "présenté concerne une charge résistive, sans résolution du courant RL."
        )

    elif tp_graphique == "Mesure des caractéristiques d'un circuit RC":
        st.subheader("Circuit RC série — réponse à un échelon")
        rc1, rc2, rc3 = st.columns(3)
        with rc1:
            r_ohm = st.number_input("Résistance R (Ω)", 1.0, 10000000.0, 1000.0, 10.0, key="rc_r")
            c_uf = st.number_input("Capacité C (µF)", 0.001, 100000.0, 100.0, 1.0, key="rc_c")
        with rc2:
            tension_echelon = st.number_input("Tension de l'échelon (V)", 0.1, 1000.0, 5.0, 0.1, key="rc_v")
            duree_tau = st.number_input("Durée affichée (multiples de τ)", 1.0, 10.0, 5.0, 0.5, key="rc_ntau")
        with rc3:
            etat_rc = st.selectbox("Régime", ["Charge", "Décharge"], key="rc_mode")
        c_f = c_uf * 1e-6
        tau = r_ohm * c_f
        temps = np.linspace(0, duree_tau * tau, 700)
        if etat_rc == "Charge":
            vc = tension_echelon * (1 - np.exp(-temps / tau))
            ic = (tension_echelon / r_ohm) * np.exp(-temps / tau)
        else:
            vc = tension_echelon * np.exp(-temps / tau)
            ic = -(tension_echelon / r_ohm) * np.exp(-temps / tau)
        c1, c2, c3 = st.columns(3)
        c1.metric("Constante de temps τ", f"{tau:.6g} s")
        c2.metric("Courant initial", f"{ic[0]*1000:.3f} mA")
        c3.metric("Tension finale", f"{vc[-1]:.3f} V")
        fig_rc = go.Figure()
        fig_rc.add_trace(go.Scatter(x=temps, y=vc, name="Tension condensateur"))
        fig_rc.add_trace(go.Scatter(x=temps, y=ic * r_ohm, name="R·i(t) (V)", yaxis="y2"))
        fig_rc.update_layout(
            title="Réponse temporelle du circuit RC",
            xaxis_title="Temps (s)", yaxis_title="Tension (V)",
            yaxis2=dict(title="R·i(t) (V)", overlaying="y", side="right"),
            height=390, legend=dict(orientation="h"),
        )
        st.plotly_chart(fig_rc, use_container_width=True)
        st.latex(r"\\tau=RC,\\quad u_C(t)=U(1-e^{-t/RC}),\\quad i(t)=\\frac{U}{R}e^{-t/RC}")
        st.caption("Modèle analytique d'un circuit RC série idéal, sans résistance interne ni fuite du condensateur.")

    elif tp_graphique == "Commande d'un moteur par Arduino":
        st.subheader("Commande basse tension — dimensionnement LED")
        a1, a2, a3 = st.columns(3)
        with a1:
            v_gpio = st.number_input("Tension GPIO (V)", 1.0, 5.5, 5.0, 0.1, key="ard_v")
            v_led = st.number_input("Chute directe LED (V)", 0.5, 4.0, 2.0, 0.1, key="ard_vf")
        with a2:
            courant_led_ma = st.number_input("Courant LED souhaité (mA)", 1.0, 30.0, 10.0, 0.5, key="ard_i")
            resistance_norm = st.number_input("Résistance installée (Ω)", 10.0, 100000.0, 330.0, 10.0, key="ard_r")
        with a3:
            tolerance = st.number_input("Tolérance résistance (%)", 1.0, 20.0, 5.0, 0.5, key="ard_tol")
        r_calc = max(0.0, (v_gpio - v_led) / (courant_led_ma / 1000))
        i_reel = max(0.0, (v_gpio - v_led) / resistance_norm) * 1000
        p_r = max(0.0, (v_gpio - v_led)**2 / resistance_norm)
        c1, c2, c3 = st.columns(3)
        c1.metric("Résistance théorique", f"{r_calc:.1f} Ω")
        c2.metric("Courant avec R installée", f"{i_reel:.2f} mA")
        c3.metric("Puissance résistance", f"{p_r*1000:.1f} mW")
        st.caption(
            f"Plage de résistance installée avec tolérance : "
            f"{resistance_norm*(1-tolerance/100):.1f} à {resistance_norm*(1+tolerance/100):.1f} Ω. "
            "Respecter les limites de courant de la broche et utiliser un étage de puissance "
            "pour toute charge inductive ou moteur."
        )


    st.subheader("🧪 Simulation logique et correction")
    st.warning(
        "La correction pédagogique vérifie la topologie et les connexions entre broches. "
        "Le solveur DC utilise les modèles permanents simplifiés décrits ci-dessus ; "
        "il ne commande aucun appareil physique réel."
    )
    if st.button("▶️ Lancer la simulation et corriger", type="primary", use_container_width=True):
        if not identite_complete:
            st.error("Renseignez Nom, Prénom, Promotion et Groupe/Section dans la barre latérale.")
        else:
            resultat_graph = analyser_circuit_graphique(
                tp_graphique, state_graph, st.session_state.bornes_par_arete
            )
            st.session_state.dernier_resultat_graphique = resultat_graph
            st.session_state.historique.append({
                "Date": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "Nom": nom.strip(), "Prénom": prenom.strip(),
                "Promotion": promotion.strip(), "Groupe": groupe.strip(),
                "TP": tp_graphique, "Note": resultat_graph["note"],
                "Résultat": "Réussi" if resultat_graph["correct"] else "À corriger",
            })

    resultat_graph = st.session_state.get("dernier_resultat_graphique")
    if resultat_graph:
        st.divider()
        if resultat_graph["correct"]:
            st.balloons()
            st.success("Montage conforme au corrigé pédagogique.")
            st.metric("Note", "20 / 20")
        else:
            st.error("Montage non conforme. Consultez les corrections.")
            st.metric("Note indicative", f'{resultat_graph["note"]:.2f} / 20')
            if resultat_graph["details"]:
                st.dataframe(pd.DataFrame(resultat_graph["details"]), use_container_width=True, hide_index=True)

elif espace == "🧪 Réaliser un TP":
    st.title("🧪 Mon espace de travaux pratiques")
    st.caption("Sélectionnez votre TP, réalisez le câblage, lancez la simulation, puis mesurez les grandeurs électriques.")

    if not identite_complete:
        st.warning("Saisissez votre matricule étudiant dans la barre latérale pour accéder à vos TP.")
        st.stop()

    if df_edt_lab.empty:
        st.error("Le fichier de l'emploi du temps est absent ou ne contient pas les colonnes attendues.")
        st.stop()

    st.success(
        f"Étudiant : {prenom} {nom} — Promotion {promotion} — "
        f"Groupe {groupe or 'non renseigné'} — Sous-groupe {sous_groupe or 'non renseigné'}"
    )

    tp_etudiant_df = _lab_tp_etudiant(etudiant_connecte, df_edt_lab)

    if tp_etudiant_df.empty:
        st.warning("Aucun TP n'est programmé pour votre promotion, votre groupe et votre sous-groupe.")
        st.stop()

    st.subheader("1. Mes travaux pratiques")

    options_tp = sorted(
        tp_etudiant_df["Enseignements"].dropna().astype(str).str.strip().unique(),
        key=lambda x: _lab_normaliser(x)
    )

    tp_choisi = st.selectbox(
        "Choisir le TP correspondant à mon emploi du temps",
        options_tp,
        key="etu_tp_choisi"
    )

    lignes_tp = tp_etudiant_df[
        tp_etudiant_df["Enseignements"].astype(str).str.strip().eq(tp_choisi)
    ].copy()

    enseignants_tp = sorted(
        {lab_nettoyer_texte(x) for x in lignes_tp["Enseignants"].tolist() if lab_nettoyer_texte(x)}
    )

    col_info1, col_info2 = st.columns(2)

    with col_info1:
        st.markdown("**Enseignants chargés du TP**")
        if enseignants_tp:
            for enseignant in enseignants_tp:
                st.markdown(f"- {enseignant}")
        else:
            st.warning("Aucun enseignant n'est renseigné pour ce TP.")

    with col_info2:
        st.markdown("**Séances programmées**")
        infos_tp = lignes_tp[["Jours", "Horaire", "Lieu"]].drop_duplicates()
        if not infos_tp.empty:
            st.dataframe(infos_tp, use_container_width=True, hide_index=True)
        else:
            st.info("Aucune séance détaillée n'est disponible.")

    tp_nom = lab_modele_simulation_depuis_tp(tp_choisi)

    if tp_nom is None or tp_nom not in TPS:
        st.info(
            "Ce TP est bien associé à votre groupe dans l'emploi du temps. "
            "Son modèle de simulation doit encore être activé par l'équipe pédagogique."
        )
        st.stop()

    tp = TPS[tp_nom]
    st.divider()

    st.subheader("2. Banc de manipulation")
    st.info(tp["description"])

    st.markdown("**Matériel et composants à utiliser**")

    colonnes_composants = st.columns(3)
    for index, composant in enumerate(tp["composants"]):
        categorie_composant = next(
            (cat for cat, elements in COMPOSANTS.items() if composant in elements),
            "Composants génériques"
        )
        bornes_composant = COMPOSANTS[categorie_composant][composant]
        fiche = fiche_composant(
            composant,
            categorie_composant,
            bornes_composant,
            "Schneider Electric"
        )

        with colonnes_composants[index % 3]:
            with st.container(border=True):
                st.markdown(f"**{composant}**")
                afficher_photo_composant(composant, fiche)
                st.caption(f"Bornes : {', '.join(bornes_composant)}")
                st.caption(fiche["fonction"])

    st.divider()

    st.subheader("3. Réalisation du câblage")

    if st.session_state.get("etu_tp_courant") != tp_nom:
        st.session_state["etu_tp_courant"] = tp_nom
        st.session_state["liaisons_etudiant"] = list(tp["liaisons"])
        st.session_state["etu_resultat_simulation"] = None

    bornes_disponibles = liste_composants_selectionnes(tp["composants"])

    if not bornes_disponibles:
        st.warning("Aucun composant n'est disponible pour ce TP.")
        st.stop()

    with st.form("form_cablage_etudiant", clear_on_submit=True):
        col_depart, col_arrivee = st.columns(2)

        with col_depart:
            borne_depart = st.selectbox(
                "Point de départ du câble",
                bornes_disponibles,
                key="etu_borne_depart"
            )

        with col_arrivee:
            borne_arrivee = st.selectbox(
                "Point d'arrivée du câble",
                bornes_disponibles,
                key="etu_borne_arrivee"
            )

        ajouter_cable = st.form_submit_button(
            "🔌 Ajouter le câble",
            use_container_width=True
        )

    if ajouter_cable:
        if borne_depart == borne_arrivee:
            st.error("Le point de départ et le point d'arrivée doivent être différents.")
        elif (borne_depart, borne_arrivee) in st.session_state.liaisons_etudiant or (
            borne_arrivee, borne_depart
        ) in st.session_state.liaisons_etudiant:
            st.warning("Cette connexion existe déjà.")
        else:
            st.session_state.liaisons_etudiant.append((borne_depart, borne_arrivee))
            st.success("Câble ajouté.")
            st.rerun()

    if st.session_state.liaisons_etudiant:
        st.markdown("**Câblage réalisé**")

        for index, (depart, arrivee) in enumerate(st.session_state.liaisons_etudiant):
            col_cable1, col_cable2, col_cable3 = st.columns([4, 4, 1])

            with col_cable1:
                st.write(f"**{depart}**")

            with col_cable2:
                st.write(f"→ **{arrivee}**")

            with col_cable3:
                if st.button("❌", key=f"etu_supprimer_cable_{index}"):
                    st.session_state.liaisons_etudiant.pop(index)
                    st.session_state["etu_resultat_simulation"] = None
                    st.rerun()
    else:
        st.info("Aucun câble n'a encore été réalisé.")

    col_reset1, col_reset2 = st.columns(2)

    with col_reset1:
        if st.button("♻️ Recharger le câblage de référence", use_container_width=True):
            st.session_state["liaisons_etudiant"] = list(tp["liaisons"])
            st.session_state["etu_resultat_simulation"] = None
            st.rerun()

    with col_reset2:
        if st.button("🧹 Vider le câblage", use_container_width=True):
            st.session_state["liaisons_etudiant"] = []
            st.session_state["etu_resultat_simulation"] = None
            st.rerun()

    st.divider()

    st.subheader("4. Simulation du montage")

    if st.button(
        "▶️ Lancer la simulation",
        type="primary",
        use_container_width=True,
        key="etu_lancer_simulation"
    ):
        resultat_cablage = corriger_montage(
            tp_nom,
            tp["composants"],
            st.session_state.liaisons_etudiant
        )

        st.session_state["etu_resultat_simulation"] = {
            "cablage": resultat_cablage,
            "branches": []
        }

        u = 24.0
        f = 50.0
        r = 100.0

        if "Graetz" in tp_nom or "Redressement" in tp_nom:
            v_moy = 0.9 * u
            i_moy = v_moy / r
            p_moy = v_moy * i_moy

            st.session_state["etu_resultat_simulation"]["branches"] = [
                {
                    "branche": "Transformateur → Pont de Graetz",
                    "tension": u,
                    "courant": i_moy,
                    "puissance": u * i_moy
                },
                {
                    "branche": "Pont de Graetz → Résistance",
                    "tension": v_moy,
                    "courant": i_moy,
                    "puissance": p_moy
                },
                {
                    "branche": "Résistance de charge",
                    "tension": v_moy,
                    "courant": i_moy,
                    "puissance": p_moy
                }
            ]

        elif "RC" in tp_nom:
            tau = r * 100e-6
            i_initial = u / r

            st.session_state["etu_resultat_simulation"]["branches"] = [
                {
                    "branche": "Source → Résistance",
                    "tension": u,
                    "courant": i_initial,
                    "puissance": u * i_initial
                },
                {
                    "branche": "Résistance → Condensateur",
                    "tension": u,
                    "courant": i_initial,
                    "puissance": u * i_initial
                },
                {
                    "branche": "Condensateur",
                    "tension": u,
                    "courant": 0.0,
                    "puissance": 0.0
                }
            ]

        elif "Arduino" in tp_nom:
            i_led = max(0.0, (5.0 - 2.0) / 330.0)

            st.session_state["etu_resultat_simulation"]["branches"] = [
                {
                    "branche": "Arduino D5 → Résistance",
                    "tension": 3.0,
                    "courant": i_led,
                    "puissance": 3.0 * i_led
                },
                {
                    "branche": "Résistance → LED",
                    "tension": 2.0,
                    "courant": i_led,
                    "puissance": 2.0 * i_led
                }
            ]

        elif "moteur asynchrone" in tp_nom.lower():
            i_nominal = 8.5
            couple = 26.0
            vitesse = 1450.0
            p_utile = couple * vitesse * 2 * math.pi / 60
            p_absorbee = p_utile / 0.86

            st.session_state["etu_resultat_simulation"]["branches"] = [
                {
                    "branche": "Réseau → Disjoncteur",
                    "tension": 400.0,
                    "courant": i_nominal,
                    "puissance": p_absorbee
                },
                {
                    "branche": "Disjoncteur → Contacteur",
                    "tension": 400.0,
                    "courant": i_nominal,
                    "puissance": p_absorbee
                },
                {
                    "branche": "Contacteur → Relais thermique",
                    "tension": 400.0,
                    "courant": i_nominal,
                    "puissance": p_absorbee
                },
                {
                    "branche": "Relais thermique → Moteur",
                    "tension": 400.0,
                    "courant": i_nominal,
                    "puissance": p_absorbee
                }
            ]

        else:
            i_dc = u / r
            p_dc = u * i_dc

            st.session_state["etu_resultat_simulation"]["branches"] = [
                {
                    "branche": "Source → Charge",
                    "tension": u,
                    "courant": i_dc,
                    "puissance": p_dc
                },
                {
                    "branche": "Charge",
                    "tension": u,
                    "courant": i_dc,
                    "puissance": p_dc
                }
            ]

    resultat_simulation = st.session_state.get("etu_resultat_simulation")

    if resultat_simulation is None:
        st.info("Réalicez le câblage puis lancez la simulation.")
    else:
        resultat_cablage = resultat_simulation["cablage"]

        if resultat_cablage["correct"]:
            st.success("✅ Câblage conforme au schéma de référence.")
        else:
            st.warning("⚠️ Le câblage comporte des différences par rapport au schéma de référence.")

        st.metric("Note indicative du câblage", f"{resultat_cablage['note']:.2f} / 20")

        if resultat_cablage["details"]:
            st.dataframe(
                pd.DataFrame(resultat_cablage["details"]),
                use_container_width=True,
                hide_index=True
            )

        st.subheader("Résultats dans les branches du montage")

        if resultat_simulation["branches"]:
            st.dataframe(
                pd.DataFrame(resultat_simulation["branches"]),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("Aucun résultat de branche disponible pour ce TP.")

    st.divider()

    st.subheader("5. Appareils de mesure et emplacement")

    if resultat_simulation is None:
        st.info("Lancez d'abord la simulation pour afficher les mesures.")
    else:
        branches_disponibles = [
            branche["branche"]
            for branche in resultat_simulation["branches"]
        ]

        appareil_mesure = st.selectbox(
            "Appareil de mesure",
            [
                "Voltmètre",
                "Ampèremètre",
                "Oscilloscope",
                "Wattmètre",
                "Tachymètre",
                "Multimètre"
            ],
            key="etu_appareil_mesure"
        )

        emplacement_mesure = st.selectbox(
            "Emplacement de l'appareil",
            branches_disponibles,
            key="etu_emplacement_mesure"
        )

        branche_mesuree = next(
            (
                branche
                for branche in resultat_simulation["branches"]
                if branche["branche"] == emplacement_mesure
            ),
            None
        )

        if branche_mesuree is None:
            st.warning("Sélectionnez une branche valide.")
        else:
            col_mesure1, col_mesure2, col_mesure3 = st.columns(3)

            if appareil_mesure == "Voltmètre":
                valeur_mesuree = branche_mesuree["tension"]
                unite_mesuree = "V"
                calibre_mesure = "20 V" if abs(valeur_mesuree) <= 20 else "200 V"
                depassement = abs(valeur_mesuree) > 200

            elif appareil_mesure == "Ampèremètre":
                valeur_mesuree = branche_mesuree["courant"]
                unite_mesuree = "A"
                calibre_mesure = "2 A" if abs(valeur_mesuree) <= 2 else "10 A"
                depassement = abs(valeur_mesuree) > 10

            elif appareil_mesure == "Wattmètre":
                valeur_mesuree = branche_mesuree["puissance"]
                unite_mesuree = "W"
                calibre_mesure = "Automatique"
                depassement = False

            elif appareil_mesure == "Tachymètre":
                valeur_mesuree = 1450.0 if "moteur" in tp_nom.lower() else 0.0
                unite_mesuree = "tr/min"
                calibre_mesure = "Automatique"
                depassement = False

            elif appareil_mesure == "Multimètre":
                valeur_mesuree = branche_mesuree["tension"]
                unite_mesuree = "V"
                calibre_mesure = "Automatique"
                depassement = False

            else:
                valeur_mesuree = branche_mesuree["tension"]
                unite_mesuree = "V"
                calibre_mesure = "Automatique"
                depassement = False

            with col_mesure1:
                st.markdown(f"**{appareil_mesure}**")
                st.caption(f"Emplacement : {emplacement_mesure}")

            with col_mesure2:
                if depassement:
                    st.error("OL — dépassement de calibre")
                else:
                    st.metric(
                        "Valeur mesurée",
                        f"{valeur_mesuree:.3g} {unite_mesuree}"
                    )

            with col_mesure3:
                st.caption(f"Calibre : {calibre_mesure}")

            if appareil_mesure == "Oscilloscope":
                st.markdown("**Visualisation du signal**")

                if "Graetz" in tp_nom or "Redressement" in tp_nom:
                    t_osc = np.linspace(0, 2 / f, 1200)
                    signal_osc = u * np.sqrt(2) * np.sin(2 * math.pi * f * t_osc)
                    titre_osc = "Tension alternative d'entrée"

                elif "RC" in tp_nom:
                    tau = r * 100e-6
                    t_osc = np.linspace(0, 5 * tau, 800)
                    signal_osc = u * (1 - np.exp(-t_osc / tau))
                    titre_osc = "Charge du condensateur"

                elif "moteur asynchrone" in tp_nom.lower():
                    t_osc = np.linspace(0, 0.04, 1000)
                    signal_osc = 325 * np.sin(2 * math.pi * 50 * t_osc)
                    titre_osc = "Tension du réseau triphasé"

                else:
                    t_osc = np.linspace(0, 0.1, 1000)
                    signal_osc = np.full_like(t_osc, u)
                    titre_osc = "Tension continue"

                fig_osc = go.Figure()
                fig_osc.add_trace(
                    go.Scatter(
                        x=t_osc * 1000,
                        y=signal_osc,
                        mode="lines",
                        name=titre_osc,
                        line=dict(color="#2563eb", width=2)
                    )
                )
                fig_osc.update_layout(
                    title=f"Oscilloscope — {titre_osc}",
                    xaxis_title="Temps (ms)",
                    yaxis_title="Tension (V)",
                    height=420,
                    margin=dict(l=10, r=10, t=45, b=10)
                )
                st.plotly_chart(fig_osc, use_container_width=True, key="etu_oscilloscope")

            elif appareil_mesure == "Tachymètre":
                if "moteur" in tp_nom.lower():
                    st.plotly_chart(
                        creer_schema_tp(tp_nom),
                        use_container_width=True,
                        key="etu_schema_tachymetre"
                    )
                else:
                    st.info("Le tachymètre est disponible uniquement pour les TP moteur.")

            else:
                st.info(
                    "La valeur affichée correspond à la branche sélectionnée "
                    "dans la simulation du montage."
                )

    st.divider()

    st.subheader("6. Schéma de référence du TP")
    st.caption(
        "Le schéma sert de repère pédagogique. Il ne révèle pas automatiquement "
        "le corrigé détaillé du câblage."
    )

    st.plotly_chart(
        creer_schema_tp(tp_nom),
        use_container_width=True,
        key="etu_schema_reference"
    )

elif espace == "ℹ️ À propos":
    st.title("ℹ️ À propos de la plateforme")
    st.markdown(
        """
        **Département d'Électrotechnique — Faculté de Génie Électrique — UDL-SBA**

        Cette application constitue une base de départ pour un laboratoire virtuel.

        **Limites de cette version :**
        - Les schémas sont représentés par une liste de connexions logiques, pas encore par un éditeur graphique.
        - Les notes et résultats sont conservés uniquement pendant la session Streamlit.
        - Les corrigés et modèles théoriques sont des exemples à valider par l'équipe pédagogique.
        - Aucune commande de puissance réelle n'est envoyée à un équipement.
        - Une authentification, une base de données et des droits enseignant/étudiant devront être ajoutés avant un déploiement officiel.
        """
    )

st.divider()
st.caption(
    "Plateforme pédagogique — Département d'Électrotechnique • "
    "Faculté de Génie Électrique • UDL-SBA"
)
