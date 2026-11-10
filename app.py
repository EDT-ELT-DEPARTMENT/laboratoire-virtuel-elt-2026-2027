# -*- coding: utf-8 -*-
"""
Plateforme de Travaux Pratiques Virtuels - Département d'Électrotechnique
Application Streamlit autonome.
"""
from __future__ import annotations

import io
import math
from datetime import datetime

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

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
        "Contacteur KM1": ["L1", "L2", "L3", "T1", "T2", "T3", "A1", "A2"],
        "Relais thermique": ["L1", "L2", "L3", "T1", "T2", "T3", "95", "96"],
        "Pont de diodes (Graetz)": ["AC1", "AC2", "DC+", "DC-"],
        "Diode de puissance": ["Anode", "Cathode"],
        "Résistance de puissance": ["Borne 1", "Borne 2"],
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
    st.header("🎓 Espace étudiant")
    nom = st.text_input("Nom", placeholder="Votre nom")
    prenom = st.text_input("Prénom", placeholder="Votre prénom")
    promotion = st.text_input("Promotion", placeholder="Ex. ING3")
    groupe = st.text_input("Groupe / Section", placeholder="Ex. G1")
    st.divider()
    espace = st.radio(
        "Navigation",
        [
            "🏠 Accueil",
            "🧪 Réaliser un TP",
            "🧰 Bibliothèque de composants",
            "📈 Mesures réelles & comparaison",
            "👨‍🏫 Espace enseignant",
            "ℹ️ À propos",
        ],
    )
    st.caption("Version pédagogique initiale — données de session non permanentes.")

identite_complete = all([nom.strip(), prenom.strip(), promotion.strip(), groupe.strip()])


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
    st.title("🧰 Bibliothèque normalisée de composants")
    st.write("Sélectionnez une catégorie pour consulter les composants et leurs bornes.")
    for categorie, elements in COMPOSANTS.items():
        with st.expander(f"📂 {categorie} — {len(elements)} composants"):
            lignes = []
            for composant, bornes in elements.items():
                lignes.append({"Composant": composant, "Bornes disponibles": " • ".join(bornes)})
            st.dataframe(pd.DataFrame(lignes), use_container_width=True, hide_index=True)

elif espace == "🧪 Réaliser un TP":
    st.title("🧪 Réalisation et validation d'un TP")
    if not identite_complete:
        st.warning("Veuillez renseigner Nom, Prénom, Promotion et Groupe/Section dans la barre latérale.")
    tp_nom = st.selectbox("Choisir le travail pratique", list(TPS.keys()))
    tp = TPS[tp_nom]
    st.info(tp["description"])

    st.subheader("1. Sélection des composants")
    composants_choisis = st.multiselect(
        "Composants utilisés dans votre montage",
        options=sorted({c for groupe_c in COMPOSANTS.values() for c in groupe_c}),
        default=tp["composants"],
        help="La sélection initiale propose les composants du corrigé. Modifiez-la pour tester la correction.",
    )
    bornes_disponibles = liste_composants_selectionnes(composants_choisis)

    st.subheader("2. Câblage virtuel")
    st.caption("Chaque ligne représente un cordon reliant deux bornes. Les liaisons sont contrôlées logiquement.")
    if not bornes_disponibles:
        st.warning("Sélectionnez d'abord des composants pour afficher leurs bornes.")
    else:
        with st.form("form_ajout_liaison", clear_on_submit=True):
            col_a, col_b = st.columns(2)
            with col_a:
                borne_depart = st.selectbox("Borne de départ", bornes_disponibles, key="borne_depart")
            with col_b:
                borne_arrivee = st.selectbox("Borne d'arrivée", bornes_disponibles, key="borne_arrivee")
            ajouter = st.form_submit_button("➕ Ajouter la liaison")
            if ajouter:
                if borne_depart == borne_arrivee:
                    st.error("Une borne ne peut pas être reliée à elle-même.")
                else:
                    st.session_state.liaisons_etudiant.append((borne_depart, borne_arrivee))
                    st.success("Liaison ajoutée.")

    if st.session_state.liaisons_etudiant:
        df_liaisons = pd.DataFrame(
            [
                {"N°": i + 1, "Départ": a, "Arrivée": b}
                for i, (a, b) in enumerate(st.session_state.liaisons_etudiant)
            ]
        )
        st.dataframe(df_liaisons, use_container_width=True, hide_index=True)
        col_del, col_clear = st.columns(2)
        with col_del:
            index_suppr = st.number_input(
                "N° de la liaison à retirer", min_value=1,
                max_value=len(st.session_state.liaisons_etudiant), value=1, step=1,
            )
            if st.button("Retirer cette liaison"):
                st.session_state.liaisons_etudiant.pop(int(index_suppr) - 1)
                st.rerun()
        with col_clear:
            if st.button("Effacer toutes les liaisons"):
                st.session_state.liaisons_etudiant = []
                st.rerun()
    else:
        st.caption("Aucune liaison ajoutée pour le moment.")

    st.subheader("3. Correction automatique")
    st.caption("Pour tester le fonctionnement, le corrigé est accessible à l'enseignant. Construisez votre propre câblage.")
    if st.button("✅ Vérifier et corriger mon montage", type="primary", use_container_width=True):
        if not identite_complete:
            st.error("Identité incomplète : renseignez vos informations dans la barre latérale.")
        else:
            resultat = corriger_montage(tp_nom, composants_choisis, st.session_state.liaisons_etudiant)
            st.session_state.dernier_resultat = resultat
            enregistrement = {
                "Date": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "Nom": nom.strip(), "Prénom": prenom.strip(),
                "Promotion": promotion.strip(), "Groupe": groupe.strip(),
                "TP": tp_nom, "Note": resultat["note"],
                "Résultat": "Réussi" if resultat["correct"] else "À corriger",
            }
            st.session_state.historique.append(enregistrement)

    resultat = st.session_state.dernier_resultat
    if resultat:
        st.divider()
        if resultat["correct"]:
            st.balloons()
            st.success("Excellent ! Tous les composants et câblages correspondent au corrigé de référence.")
            st.metric("Note obtenue", "20 / 20")
        else:
            st.warning("Votre montage comporte des erreurs. Consultez le tableau de correction ci-dessous.")
            st.metric("Note indicative", f'{resultat["note"]:.2f} / 20')
            if resultat["details"]:
                st.dataframe(pd.DataFrame(resultat["details"]), use_container_width=True, hide_index=True)
            else:
                st.success("Aucune erreur détectée.")

elif espace == "📈 Mesures réelles & comparaison":
    st.title("📈 Comparaison théorie / expérience")
    st.write(
        "Importez un fichier de mesures. Choisissez les colonnes de l'axe X et de la mesure Y, "
        "puis sélectionnez un modèle théorique pédagogique."
    )
    fichier = st.file_uploader(
        "Importer les mesures expérimentales",
        type=["xlsx", "xls", "csv"],
        help="Formats acceptés : Excel .xlsx/.xls et CSV.",
    )

    if fichier is not None:
        try:
            if fichier.name.lower().endswith(".csv"):
                try:
                    donnees = pd.read_csv(fichier, sep=None, engine="python")
                except UnicodeDecodeError:
                    fichier.seek(0)
                    donnees = pd.read_csv(fichier, sep=None, engine="python", encoding="latin-1")
            else:
                donnees = pd.read_excel(fichier)
            donnees = donnees.dropna(how="all")
            st.subheader("Aperçu des données")
            st.dataframe(donnees.head(20), use_container_width=True)
            colonnes = list(donnees.columns)
            if len(colonnes) >= 2:
                colx, coly = st.columns(2)
                with colx:
                    axe_x = st.selectbox("Colonne de l'axe X", colonnes, index=0)
                with coly:
                    axe_y = st.selectbox("Colonne de la mesure Y", colonnes, index=1)
                modele = st.selectbox(
                    "Modèle théorique de référence",
                    [
                        "Sinusoïde",
                        "Redressement double alternance",
                        "Réponse indicielle RC (charge)",
                        "Vitesse moteur (montée simplifiée)",
                        "Valeur constante",
                    ],
                )
                amplitude = st.number_input("Amplitude théorique", value=10.0, step=1.0)
                parametre = st.number_input(
                    "Paramètre du modèle (fréquence / constante de temps)",
                    min_value=0.001, value=1.0, step=0.1,
                )
                if st.button("📊 Tracer et comparer", type="primary"):
                    travail = donnees[[axe_x, axe_y]].copy()
                    travail[axe_x] = pd.to_numeric(travail[axe_x], errors="coerce")
                    travail[axe_y] = pd.to_numeric(travail[axe_y], errors="coerce")
                    travail = travail.dropna().sort_values(axe_x)
                    if len(travail) < 2:
                        st.error("Il faut au moins deux lignes numériques valides.")
                    else:
                        x = travail[axe_x].to_numpy(dtype=float)
                        y = travail[axe_y].to_numpy(dtype=float)
                        t = x - np.min(x)
                        if modele == "Sinusoïde":
                            y_theorie = amplitude * np.sin(2 * np.pi * parametre * t)
                        elif modele == "Redressement double alternance":
                            y_theorie = np.abs(amplitude * np.sin(2 * np.pi * parametre * t))
                        elif modele == "Réponse indicielle RC (charge)":
                            y_theorie = amplitude * (1 - np.exp(-t / parametre))
                        elif modele == "Vitesse moteur (montée simplifiée)":
                            y_theorie = amplitude * (1 - np.exp(-t / parametre))
                        else:
                            y_theorie = np.full_like(x, amplitude, dtype=float)

                        ecart_abs = np.abs(y - y_theorie)
                        masque = np.abs(y_theorie) > 1e-9
                        erreurs_relatives = (ecart_abs[masque] / np.abs(y_theorie[masque])) * 100
                        erreur_moyenne = float(np.mean(erreurs_relatives)) if len(erreurs_relatives) else float("nan")
                        rmse = float(np.sqrt(np.mean((y - y_theorie) ** 2)))

                        figure = go.Figure()
                        figure.add_trace(go.Scatter(x=x, y=y_theorie, mode="lines", name="Théorie"))
                        figure.add_trace(go.Scatter(x=x, y=y, mode="lines+markers", name="Mesures réelles"))
                        figure.update_layout(
                            title="Comparaison entre modèle théorique et mesures expérimentales",
                            xaxis_title=str(axe_x), yaxis_title=str(axe_y),
                            legend_title="Séries", hovermode="x unified",
                        )
                        st.plotly_chart(figure, use_container_width=True)
                        m1, m2, m3 = st.columns(3)
                        m1.metric("Erreur relative moyenne", "Non calculable" if math.isnan(erreur_moyenne) else f"{erreur_moyenne:.2f} %")
                        m2.metric("RMSE", f"{rmse:.4g}")
                        m3.metric("Nombre de mesures", len(y))
                        rapport = travail.copy()
                        rapport["Théorie"] = y_theorie
                        rapport["Écart absolu"] = ecart_abs
                        rapport["Erreur relative (%)"] = np.where(
                            np.abs(y_theorie) > 1e-9,
                            ecart_abs / np.abs(y_theorie) * 100,
                            np.nan,
                        )
                        st.download_button(
                            "⬇️ Télécharger le rapport comparatif CSV",
                            data=rapport.to_csv(index=False).encode("utf-8-sig"),
                            file_name="rapport_comparaison_theorie_experience.csv",
                            mime="text/csv",
                        )
                        st.caption(
                            "Le modèle théorique sélectionné est une référence simplifiée. "
                            "Pour une validation scientifique, utilisez l'équation exacte du TP, "
                            "les paramètres nominaux et les unités correctes."
                        )
            else:
                st.error("Le fichier doit contenir au moins deux colonnes.")
        except Exception as exc:
            st.error(f"Impossible de lire le fichier : {exc}")
            st.info("Vérifiez le format, les en-têtes et l'absence de fichier protégé par mot de passe.")

elif espace == "👨‍🏫 Espace enseignant":
    st.title("👨‍🏫 Espace enseignant")
    st.warning(
        "Cette première version n'intègre pas encore d'authentification enseignant. "
        "Ne publiez pas de corrigés confidentiels dans cette page avant l'ajout d'un contrôle d'accès."
    )
    st.subheader("Résultats de la session actuelle")
    if st.session_state.historique:
        historique = pd.DataFrame(st.session_state.historique)
        st.dataframe(historique, use_container_width=True, hide_index=True)
        col1, col2, col3 = st.columns(3)
        col1.metric("Tentatives", len(historique))
        col2.metric("Note moyenne", f'{historique["Note"].mean():.2f} / 20')
        col3.metric("Montages réussis", int((historique["Résultat"] == "Réussi").sum()))
        st.download_button(
            "⬇️ Exporter les résultats CSV",
            data=historique.to_csv(index=False).encode("utf-8-sig"),
            file_name="resultats_tp_etudiants.csv",
            mime="text/csv",
        )
    else:
        st.info("Aucune tentative enregistrée dans cette session Streamlit.")

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
