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

    return DOSSIER_PHOTOS_RACINE / f"{slug}.jpg"

DESCRIPTIONS_COMPOSANTS = {
    "Moteur asynchrone triphasé": ("Convertit l'énergie électrique triphasée en énergie mécanique par induction électromagnétique.", "Moteur triphasé", "Plaque signalétique : tension, couplage Δ/Y, puissance, courant, fréquence, cos φ, rendement et vitesse.", "U1, V1, W1 : début des enroulements ; U2, V2, W2 : fins ; PE : terre de protection.", "Entraînement de pompes, ventilateurs, convoyeurs et machines industrielles."),
    "Transformateur monophasé": ("Transfère l'énergie alternative entre deux circuits par induction électromagnétique.", "Transformateur", "Plaque : puissances apparente (VA), tensions primaire/secondaire, fréquence et courant nominal.", "P1-P2 : primaire ; S1-S2 : secondaire.", "Adaptation de tension, isolation galvanique et alimentation de montages."),
    "Contacteur KM1": ("Appareil électromécanique commandé par une bobine permettant d'établir ou couper un circuit de puissance.", "Contacteur", "Tension bobine A1-A2, tension assignée, courant d'emploi, catégorie d'emploi (ex. AC-3) et nombre de pôles selon référence.", "L1/L2/L3 : arrivée ; T1/T2/T3 : départ ; A1/A2 : bobine ; 13-14 : auxiliaire NO.", "Commande fréquente de moteurs et de charges électriques."),
    "Relais thermique": ("Protège un moteur contre les surcharges prolongées en détectant l'échéchauffement lié au courant.", "Relais thermique", "Plage de réglage en ampères, classe de déclenchement, tension/courant des contacts auxiliaires selon référence.", "L1/L2/L3 : entrée ; T1/T2/T3 : sortie ; 95-96 : contact NF de défaut.", "Protection contre les surcharges moteur, généralement associé à un contacteur."),
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
    """Place automatiquement dans le canevas tous les appareils requis par le TP."""
    tp = TPS.get(nom_tp, {})
    composants_tp = tp.get("composants", [])
    if not composants_tp:
        return

    for nom in composants_tp:
        ajouter_composant_graphique(nom, marque=marque)

    st.session_state.bornes_par_arete = {}
    st.session_state.couleurs_fils_par_arete = {}
    st.session_state.pop("dernier_resultat_graphique", None)


def construire_circuit_reference_enseignant(nom_tp, marque="Schneider Electric"):
    """Construit le canevas de référence pré-câblé, réservé à l'enseignant."""
    if not STREAMLIT_FLOW_DISPONIBLE:
        return None, {}
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

    index_broches = {}
    for node in state.nodes:
        data = node.data or {}
        if data.get("node_role") == "borne":
            index_broches[(data.get("component"), data.get("terminal"))] = node.id
        elif data.get("node_role") == "composant":
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
    nb_composants = sum(1 for n in state.nodes if n.data.get("node_role") == "composant")
    x0 = 80 + (nb_composants % 2) * 650
    y0 = 60 + (nb_composants // 2) * 620

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
# ---------------------------------------------------------------------
def resoudre_circuit_dc(state, bornes_par_arete, parametres, noeud_masse):
    """Solveur MNA DC permanent : R, sources, bobines, moteurs simplifiés, contacts et diodes idéalisées."""
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
            add_r(cid, f"{ident} — bobine A1/A2", "A1", "A2", float(par.get("coil_r",1000.0)), "Bobine de contacteur")

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
        rows.append({"Com
