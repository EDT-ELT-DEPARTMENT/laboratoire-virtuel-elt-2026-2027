# -*- coding: utf-8 -*-
"""
Plateforme de Travaux Pratiques Virtuels - Département d'Électrotechnique
Application Streamlit autonome.
"""
from __future__ import annotations

import io
import math
from datetime import datetime
from uuid import uuid4

try:
    from streamlit_flow import streamlit_flow
    from streamlit_flow.elements import StreamlitFlowNode, StreamlitFlowEdge
    from streamlit_flow.state import StreamlitFlowState
    STREAMLIT_FLOW_DISPONIBLE = True
except Exception:
    STREAMLIT_FLOW_DISPONIBLE = False

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
    "tp_graphique_courant": None,
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
            "🧩 Éditeur graphique de circuits",
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



def initialiser_circuit_graphique():
    if st.session_state.circuit_graphique is None:
        st.session_state.circuit_graphique = StreamlitFlowState(nodes=[], edges=[])


def ajouter_composant_graphique(nom_composant):
    state = st.session_state.circuit_graphique
    bornes = next((elements[nom_composant] for elements in COMPOSANTS.values()
                   if nom_composant in elements), [])
    if not bornes:
        st.error("Composant introuvable dans la bibliothèque.")
        return
    node_id = f"cmp_{uuid4().hex[:10]}"
    position = (80 + (len(state.nodes) % 3) * 260, 60 + (len(state.nodes) // 3) * 180)
    numero = 1 + sum(1 for n in state.nodes if getattr(n, "data", {}).get("component") == nom_composant)
    instance = f"{nom_composant} #{numero}"
    pastilles = "".join(
        f"<span style='display:inline-block;margin:3px 3px 0 0;padding:3px 6px;"
        f"border:1px solid #60a5fa;border-radius:6px;background:#eff6ff;"
        f"font-size:10px;color:#1e3a8a'>{borne}</span>"
        for borne in bornes
    )
    contenu = (
        f"<div style='padding:9px;min-width:190px;max-width:260px'>"
        f"<div style='font-weight:700;font-size:14px;color:#0f172a'>⚡ {instance}</div>"
        f"<div style='font-size:10px;color:#475569;margin-top:6px'>BORNES ÉLECTRIQUES</div>"
        f"<div style='margin-top:2px;line-height:1.9'>{pastilles}</div></div>"
    )
    node = StreamlitFlowNode(
        node_id, position,
        {"content": contenu, "component": nom_composant, "instance": instance, "terminals": bornes},
        "default", "right", "left",
    )
    state.nodes.append(node)
    st.session_state.circuit_graphique = state


def analyser_circuit_graphique(tp_nom, state, bornes_par_arete):
    reference = TPS[tp_nom]
    nodes = {n.id: n for n in state.nodes}
    composants_presents = {
        n.data.get("component") for n in state.nodes if getattr(n, "data", None)
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
        depart, arrivee = choix
        n1, n2 = nodes.get(edge.source), nodes.get(edge.target)
        if n1 is None or n2 is None:
            continue
        liaisons_reelles.add(normaliser_liaison(
            f"{n1.data.get('component')}.{depart}",
            f"{n2.data.get('component')}.{arrivee}"
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
# Modèle limité aux résistances et sources indépendantes DC idéales.
# Les fils idéaux fusionnent les bornes en un même nœud électrique.
# ---------------------------------------------------------------------
def resoudre_circuit_dc(state, bornes_par_arete, parametres, noeud_masse):
    """Résout un réseau R/V/I en DC. Retourne tensions et courants orientés + vers -."""
    nodes = {n.id: n for n in state.nodes}
    parent = {}

    def find(x):
        parent.setdefault(x, x)
        if parent[x] != x:
            parent[x] = find(parent[x])
        return parent[x]

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for node in state.nodes:
        for terminal in node.data.get("terminals", []):
            find(f"{node.id}::{terminal}")

    for edge in state.edges:
        selected = bornes_par_arete.get(edge.id)
        if not selected:
            continue
        a, b = selected
        if edge.source in nodes and edge.target in nodes:
            union(f"{edge.source}::{a}", f"{edge.target}::{b}")

    net_labels = {}
    for node in state.nodes:
        for terminal in node.data.get("terminals", []):
            key = f"{node.id}::{terminal}"
            root = find(key)
            net_labels.setdefault(root, f"N{len(net_labels) + 1}")

    elements = []
    for node in state.nodes:
        typ = node.data.get("component")
        if typ not in ("Résistance", "Résistance de puissance", "Source de tension DC", "Source de courant DC"):
            continue
        terminals = node.data.get("terminals", [])
        if len(terminals) < 2:
            continue
        nplus = net_labels[find(f"{node.id}::{terminals[0]}")]
        nminus = net_labels[find(f"{node.id}::{terminals[1]}")]
        values = parametres.get(node.id, {})
        elements.append({
            "id": node.id, "nom": node.data.get("instance", typ), "type": typ,
            "plus": nplus, "minus": nminus,
            "valeur": float(values.get("value", 0.0)),
        })

    nets = sorted(set(net_labels.values()))
    if noeud_masse not in nets:
        raise ValueError("Le nœud de référence choisi n'existe plus.")
    if not elements:
        raise ValueError("Ajoutez au moins une résistance ou une source DC prise en charge.")

    unknown_nets = [n for n in nets if n != noeud_masse]
    index = {net: i for i, net in enumerate(unknown_nets)}
    voltage_sources = [e for e in elements if e["type"] == "Source de tension DC"]
    size = len(unknown_nets) + len(voltage_sources)
    if size == 0:
        raise ValueError("Le circuit ne contient aucun nœud électrique calculable.")
    matrix = np.zeros((size, size), dtype=float)
    rhs = np.zeros(size, dtype=float)

    def stamp_conductance(a, b, g):
        if a != noeud_masse:
            ia = index[a]
            matrix[ia, ia] += g
        if b != noeud_masse:
            ib = index[b]
            matrix[ib, ib] += g
        if a != noeud_masse and b != noeud_masse:
            ia, ib = index[a], index[b]
            matrix[ia, ib] -= g
            matrix[ib, ia] -= g

    for e in elements:
        a, b, value = e["plus"], e["minus"], e["valeur"]
        if a == b:
            raise ValueError(f"{e['nom']} est court-circuité : ses deux bornes sont sur le même nœud.")
        if e["type"] in ("Résistance", "Résistance de puissance"):
            if value <= 0:
                raise ValueError(f"La valeur de {e['nom']} doit être supérieure à 0 Ω.")
            stamp_conductance(a, b, 1.0 / value)
        elif e["type"] == "Source de courant DC":
            # Courant positif orienté de la borne + vers la borne -.
            if a != noeud_masse:
                rhs[index[a]] -= value
            if b != noeud_masse:
                rhs[index[b]] += value

    for k, e in enumerate(voltage_sources):
        row = len(unknown_nets) + k
        a, b = e["plus"], e["minus"]
        if a != noeud_masse:
            ia = index[a]
            matrix[ia, row] += 1.0
            matrix[row, ia] += 1.0
        if b != noeud_masse:
            ib = index[b]
            matrix[ib, row] -= 1.0
            matrix[row, ib] -= 1.0
        rhs[row] = e["valeur"]

    try:
        solution = np.linalg.solve(matrix, rhs)
    except np.linalg.LinAlgError as exc:
        raise ValueError("Circuit singulier : vérifiez les fils, la masse, les sources et les chemins résistifs (nœud flottant ou source idéale en conflit).") from exc

    tensions = {noeud_masse: 0.0}
    for net, i in index.items():
        tensions[net] = float(solution[i])
    courants_sources_tension = {
        e["id"]: float(solution[len(unknown_nets) + k])
        for k, e in enumerate(voltage_sources)
    }
    rows = []
    for e in elements:
        va, vb = tensions[e["plus"]], tensions[e["minus"]]
        if e["type"] in ("Résistance", "Résistance de puissance"):
            courant = (va - vb) / e["valeur"]
            puissance = (va - vb) * courant
        elif e["type"] == "Source de courant DC":
            courant = e["valeur"]
            puissance = (va - vb) * courant
        else:
            courant = courants_sources_tension[e["id"]]
            puissance = (va - vb) * courant
        rows.append({
            "Composant": e["nom"], "Type": e["type"],
            "Nœud +": e["plus"], "Nœud -": e["minus"],
            "Tension (V)": va - vb, "Courant (+ vers -) (A)": courant,
            "Puissance absorbée (W)": puissance,
        })
    return tensions, pd.DataFrame(rows)



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
    st.title("🧰 Bibliothèque normalisée de composants")
    st.write("Sélectionnez une catégorie pour consulter les composants et leurs bornes.")
    for categorie, elements in COMPOSANTS.items():
        with st.expander(f"📂 {categorie} — {len(elements)} composants"):
            lignes = []
            for composant, bornes in elements.items():
                lignes.append({"Composant": composant, "Bornes disponibles": " • ".join(bornes)})
            st.dataframe(pd.DataFrame(lignes), use_container_width=True, hide_index=True)

elif espace == "🧩 Éditeur graphique de circuits":
    st.title("🧩 Atelier graphique de câblage électrique")
    st.write(
        "Ajoutez les appareils dans le canevas, déplacez-les, puis tirez un fil "
        "d'une poignée de sortie vers une poignée d'entrée. Affectez ensuite les bornes "
        "exactes et lancez la correction."
    )
    if not STREAMLIT_FLOW_DISPONIBLE:
        st.error("Module absent : ajoutez streamlit-flow-component==1.6.1 à requirements.txt.")
        st.stop()

    initialiser_circuit_graphique()
    tp_graphique = st.selectbox("TP de référence", list(TPS.keys()), key="tp_graphique_select")
    if st.session_state.tp_graphique_courant != tp_graphique:
        st.session_state.tp_graphique_courant = tp_graphique
        st.session_state.circuit_graphique = StreamlitFlowState(nodes=[], edges=[])
        st.session_state.bornes_par_arete = {}
        st.session_state.pop("dernier_resultat_graphique", None)

    st.info(TPS[tp_graphique]["description"])
    col_bib, col_canvas = st.columns([1, 3], gap="large")
    with col_bib:
        st.subheader("🧰 Bibliothèque")
        categorie_graph = st.selectbox("Catégorie", list(COMPOSANTS.keys()), key="cat_graphique")
        composant_graph = st.selectbox("Composant", list(COMPOSANTS[categorie_graph].keys()), key="composant_graphique")
        if st.button("➕ Placer dans le circuit", use_container_width=True):
            ajouter_composant_graphique(composant_graph)
            st.rerun()
        st.divider()
        st.caption("Composants attendus pour ce TP")
        for item in TPS[tp_graphique]["composants"]:
            st.write(f"• {item}")
        if st.button("🗑️ Réinitialiser le canevas", use_container_width=True):
            st.session_state.circuit_graphique = StreamlitFlowState(nodes=[], edges=[])
            st.session_state.bornes_par_arete = {}
            st.session_state.pop("dernier_resultat_graphique", None)
            st.rerun()

    with col_canvas:
        st.subheader("⚙️ Zone de câblage")
        st.caption("Glissez les blocs pour les déplacer. Reliez les poignées droite et gauche pour créer un fil.")
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

    st.subheader("🔌 Bornes utilisées pour chaque fil")
    if not state_graph.nodes:
        st.warning("Le canevas est vide : placez les composants à gauche.")
    elif not state_graph.edges:
        st.info("Aucun fil : reliez deux composants dans le canevas.")
    else:
        noeuds = {n.id: n for n in state_graph.nodes}
        for edge in state_graph.edges:
            n1, n2 = noeuds.get(edge.source), noeuds.get(edge.target)
            if not n1 or not n2:
                continue
            nom1, nom2 = n1.data.get("component", n1.id), n2.data.get("component", n2.id)
            bornes1, bornes2 = n1.data.get("terminals", []), n2.data.get("terminals", [])
            valeur = st.session_state.bornes_par_arete.get(edge.id, (bornes1[0], bornes2[0]))
            st.markdown(f"**Fil : {nom1} → {nom2}**")
            ca, cb = st.columns(2)
            with ca:
                choix1 = st.selectbox(
                    f"Borne sur {nom1}", bornes1,
                    index=bornes1.index(valeur[0]) if valeur[0] in bornes1 else 0,
                    key=f"src_terminal_{edge.id}",
                )
            with cb:
                choix2 = st.selectbox(
                    f"Borne sur {nom2}", bornes2,
                    index=bornes2.index(valeur[1]) if valeur[1] in bornes2 else 0,
                    key=f"dst_terminal_{edge.id}",
                )
            st.session_state.bornes_par_arete[edge.id] = (choix1, choix2)
            st.divider()

    st.divider()
    st.header("🔬 Simulation du circuit réellement câblé — solveur DC")
    st.markdown(
        "Les fils du canevas sont utilisés pour fusionner les bornes en nœuds électriques. "
        "Le solveur calcule ensuite les tensions, courants et puissances pour les résistances "
        "et sources indépendantes continues."
    )
    supported_nodes = [
        n for n in state_graph.nodes
        if n.data.get("component") in (
            "Résistance", "Résistance de puissance", "Source de tension DC", "Source de courant DC"
        )
    ]
    parametres_dc = {}
    if supported_nodes:
        st.subheader("Paramètres des composants simulés")
        for node in supported_nodes:
            typ = node.data.get("component")
            ident = node.data.get("instance", typ)
            default_value = 100.0 if typ in ("Résistance", "Résistance de puissance") else (12.0 if typ == "Source de tension DC" else 0.1)
            unit = "Ω" if "Résistance" in typ else ("V" if typ == "Source de tension DC" else "A")
            valeur = st.number_input(
                f"{ident} — valeur ({unit})", min_value=0.000001,
                max_value=100000000.0, value=float(default_value), format="%.6g",
                key=f"dc_value_{node.id}"
            )
            parametres_dc[node.id] = {"value": valeur}

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
            for terminal in node.data.get("terminals", []):
                find_mesure(f"{node.id}::{terminal}")
        for edge in state_graph.edges:
            pair = st.session_state.bornes_par_arete.get(edge.id)
            if pair and edge.source in {n.id for n in state_graph.nodes} and edge.target in {n.id for n in state_graph.nodes}:
                union_mesure(f"{edge.source}::{pair[0]}", f"{edge.target}::{pair[1]}")
        racines = {}
        terminal_vers_noeud = {}
        for node in state_graph.nodes:
            for terminal in node.data.get("terminals", []):
                cle = f"{node.id}::{terminal}"
                racine = find_mesure(cle)
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
        st.info("Ajoutez au moins une résistance ou une source DC pour lancer le solveur. Les autres composants restent visibles dans le laboratoire, mais ne sont pas encore modélisés par ce solveur.")

    st.warning(
        "Limite de cette étape : les bornes sont affichées sur les blocs et chaque fil est "
        "affecté à deux bornes dans la liste de configuration. La bibliothèque Streamlit Flow "
        "utilisée ici ne fournit pas, dans cette intégration, de poignées graphiques indépendantes "
        "sur chaque broche. Le solveur DC ne modélise que R/V/I idéaux ; il ne calcule pas encore "
        "les moteurs, contacteurs, diodes, condensateurs ou bobines."
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
        u_moy = float(np.trapz(vo, t) / (t[-1] - t[0]))
        u_eff = float(math.sqrt(np.trapz(vo**2, t) / (t[-1] - t[0])))
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


    st.divider()
    st.header("🧮 Solveur électrique DC — calcul à partir du câblage")
    st.caption(
        "Le solveur lit les fils du canevas et fusionne les bornes reliées. "
        "Il résout les circuits résistifs linéaires avec sources DC idéales. "
        "Les moteurs, contacteurs, diodes, condensateurs et bobines ne sont pas encore modélisés dans ce solveur."
    )
    noeuds_solveur = {n.id: n for n in state_graph.nodes}
    elements_solveur = [n for n in state_graph.nodes if n.data.get("component") in (
        "Résistance", "Résistance de puissance", "Source de tension DC", "Source de courant DC"
    )]
    if not elements_solveur:
        st.info("Placez au moins une résistance et une source DC depuis la bibliothèque pour utiliser ce solveur.")
    else:
        params_dc = {}
        for element in elements_solveur:
            nom_element = element.data.get("instance", element.data.get("component"))
            typ_element = element.data.get("component")
            if typ_element in ("Résistance", "Résistance de puissance"):
                valeur = st.number_input(f"{nom_element} — valeur (Ω)", min_value=0.001, value=100.0, step=1.0, key=f"dc_{element.id}")
            elif typ_element == "Source de tension DC":
                valeur = st.number_input(f"{nom_element} — tension (+ vers -) (V)", value=12.0, step=1.0, key=f"dc_{element.id}")
            else:
                valeur = st.number_input(f"{nom_element} — courant (+ vers -) (A)", value=0.1, step=0.01, key=f"dc_{element.id}")
            params_dc[element.id] = {"value": valeur}

        # Construire les réseaux pour proposer le choix de la masse.
        parent_ui = {}
        def root_ui(x):
            parent_ui.setdefault(x, x)
            if parent_ui[x] != x:
                parent_ui[x] = root_ui(parent_ui[x])
            return parent_ui[x]
        def join_ui(a, b):
            ra, rb = root_ui(a), root_ui(b)
            if ra != rb:
                parent_ui[rb] = ra
        for node in state_graph.nodes:
            for terminal in node.data.get("terminals", []):
                root_ui(f"{node.id}::{terminal}")
        for edge in state_graph.edges:
            pair = st.session_state.bornes_par_arete.get(edge.id)
            if pair and edge.source in noeuds_solveur and edge.target in noeuds_solveur:
                join_ui(f"{edge.source}::{pair[0]}", f"{edge.target}::{pair[1]}")
        net_names = {}
        for node in state_graph.nodes:
            for terminal in node.data.get("terminals", []):
                rt = root_ui(f"{node.id}::{terminal}")
                net_names.setdefault(rt, f"N{len(net_names)+1}")
        nets_choices = sorted(set(net_names.values()))
        if nets_choices:
            masse = st.selectbox("Nœud de référence (masse 0 V)", nets_choices, key="dc_ground")
            if st.button("▶️ Résoudre le circuit DC", type="primary", key="run_dc_solver"):
                try:
                    tensions_dc, tableau_dc = resoudre_circuit_dc(
                        state_graph, st.session_state.bornes_par_arete, params_dc, masse
                    )
                    st.success("Résolution DC terminée.")
                    st.subheader("Tensions des nœuds")
                    st.dataframe(pd.DataFrame([{"Nœud": k, "Tension (V)": v} for k, v in sorted(tensions_dc.items())]), use_container_width=True, hide_index=True)
                    st.subheader("Courants et puissances des composants")
                    st.dataframe(tableau_dc, use_container_width=True, hide_index=True)
                    st.metric("Puissance totale absorbée nette", f"{tableau_dc['Puissance absorbée (W)'].sum():.6g} W")
                    st.caption("Convention : courant positif de la borne + vers la borne -. Une puissance négative signifie que le composant fournit de l'énergie au circuit.")
                except Exception as erreur_dc:
                    st.error(f"Impossible de résoudre ce montage : {erreur_dc}")

    st.subheader("🧪 Simulation logique et correction")
    st.warning(
        "La correction pédagogique vérifie la topologie. Le solveur DC séparé résout "
        "les réseaux R/V/I pris en charge à partir des fils. Aucun appareil physique n'est commandé."
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
    st.title("🧪 Réalisation et validation d'un TP")
    if not identite_complete:
        st.warning("Veuillez renseigner Nom, Prénom, Promotion et Groupe/Section dans la barre latérale.")

    tp_nom = st.selectbox("Choisir le travail pratique", list(TPS.keys()), key="tp_realiser_select")
    tp = TPS[tp_nom]
    if st.session_state.get("tp_realiser_courant") != tp_nom:
        st.session_state.tp_realiser_courant = tp_nom
        st.session_state.liaisons_etudiant = list(tp["liaisons"])
        st.session_state.dernier_resultat = None
        st.session_state.composants_tp_personnalises = list(tp["composants"])
    st.info(tp["description"])

    st.subheader("Schéma du TP chargé automatiquement")
    st.caption("Le schéma ci-dessous affiche immédiatement les composants et les connexions du montage de référence. Il sert de point de départ ; vous pouvez ensuite créer votre propre montage.")
    st.plotly_chart(creer_schema_tp(tp_nom), use_container_width=True, key="schema_tp_auto")
    with st.expander("Voir les connexions du schéma de référence"):
        st.dataframe(pd.DataFrame([{"Borne de départ": a, "Borne d'arrivée": b} for a, b in tp["liaisons"]]), use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("1. Créer ou modifier votre propre montage")
    mode_montage = st.radio(
        "Mode de travail", ["Partir du schéma fourni", "Créer un montage personnel"],
        horizontal=True, key="mode_montage_tp"
    )
    if mode_montage == "Créer un montage personnel":
        if st.button("Nouveau montage vierge", key="nouveau_montage_vierge"):
            st.session_state.liaisons_etudiant = []
            st.session_state.composants_tp_personnalises = []
            st.rerun()
        defauts_composants = st.session_state.get("composants_tp_personnalises", [])
    else:
        defauts_composants = list(tp["composants"])
        st.session_state.composants_tp_personnalises = list(tp["composants"])
        if not st.session_state.liaisons_etudiant:
            st.session_state.liaisons_etudiant = list(tp["liaisons"])

    tous_composants = sorted({c for groupe_c in COMPOSANTS.values() for c in groupe_c})
    composants_choisis = st.multiselect(
        "Composants placés sur votre plan de travail", options=tous_composants,
        default=[c for c in defauts_composants if c in tous_composants],
        key=f"composants_tp_multiselect_{tp_nom}_{mode_montage}",
        help="Le mode TP charge les composants de référence. En montage personnel, choisissez librement les composants."
    )
    st.session_state.composants_tp_personnalises = list(composants_choisis)
    bornes_disponibles = liste_composants_selectionnes(composants_choisis)

    st.markdown("**Ajouter un fil entre deux bornes**")
    if not bornes_disponibles:
        st.warning("Ajoutez au moins un composant pour afficher ses bornes.")
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
                elif (borne_depart, borne_arrivee) in st.session_state.liaisons_etudiant or (borne_arrivee, borne_depart) in st.session_state.liaisons_etudiant:
                    st.warning("Cette liaison existe déjà.")
                else:
                    st.session_state.liaisons_etudiant.append((borne_depart, borne_arrivee))
                    st.success("Liaison ajoutée.")
                    st.rerun()

    if st.session_state.liaisons_etudiant:
        st.dataframe(pd.DataFrame([
            {"N°": i + 1, "Départ": a, "Arrivée": b}
            for i, (a, b) in enumerate(st.session_state.liaisons_etudiant)
        ]), use_container_width=True, hide_index=True)
        cdel, cclear = st.columns(2)
        with cdel:
            idx = st.number_input("N° de la liaison à retirer", min_value=1,
                                  max_value=len(st.session_state.liaisons_etudiant), value=1, step=1,
                                  key="liaison_a_supprimer_tp")
            if st.button("Retirer cette liaison", key="retirer_liaison_tp"):
                st.session_state.liaisons_etudiant.pop(int(idx) - 1)
                st.rerun()
        with cclear:
            if st.button("Effacer toutes les liaisons", key="effacer_liaisons_tp"):
                st.session_state.liaisons_etudiant = []
                st.rerun()

    st.divider()
    st.subheader("2. Mesures et tracé des courbes")
    st.caption("Choisissez le type de mesure et les bornes où placer les sondes. Les courbes sont des modèles pédagogiques du TP sélectionné ; elles ne prétendent pas être une mesure électrique issue d'un appareil réel tant que le circuit n'est pas résolu par le simulateur correspondant.")
    type_mesure = st.selectbox("Appareil / grandeur à mesurer", ["Tension entre deux bornes (voltmètre)", "Courant dans un composant (ampèremètre)", "Tracer le signal temporel à l'oscilloscope"], key="type_mesure_tp")
    borne_a = borne_b = "Non sélectionnée"
    composant_courant = composants_choisis[0] if composants_choisis else "Aucun composant"
    if "Tension" in type_mesure or "oscilloscope" in type_mesure.lower():
        if bornes_disponibles:
            mc1, mc2 = st.columns(2)
            with mc1:
                borne_a = st.selectbox("Sonde positive / CH1+", bornes_disponibles, key="sonde_positive_tp")
            with mc2:
                borne_b = st.selectbox("Sonde négative / référence", bornes_disponibles, key="sonde_negative_tp")
            if borne_a == borne_b:
                st.warning("Choisissez deux bornes différentes pour mesurer une différence de potentiel.")
    else:
        if composants_choisis:
            composant_courant = st.selectbox("Composant traversé par le courant", composants_choisis, key="composant_mesure_courant_tp")
    if st.button("📈 Tracer la courbe", type="primary", key="tracer_courbe_sonde_tp"):
        if not bornes_disponibles:
            st.error("Ajoutez des composants avant de placer une sonde.")
        elif ("Tension" in type_mesure or "oscilloscope" in type_mesure.lower()) and borne_a == borne_b:
            st.error("Les deux sondes doivent être placées sur des bornes différentes.")
        else:
            st.session_state.courbe_sonde_tp = {
                "type": type_mesure, "a": borne_a, "b": borne_b,
                "composant": composant_courant, "tp": tp_nom,
            }
    sonde = st.session_state.get("courbe_sonde_tp")
    if sonde and sonde.get("tp") == tp_nom:
        st.plotly_chart(tracer_courbe_sonde(tp_nom, sonde["type"], sonde["a"], sonde["b"], sonde["composant"]), use_container_width=True)
        st.caption(f"Sonde sélectionnée : {sonde['type']} · {sonde['a']} / {sonde['b']} · composant : {sonde['composant']}")

    st.divider()
    st.subheader("3. Correction automatique du montage")
    st.caption("La correction compare votre sélection et vos connexions au schéma de référence du TP.")
    if st.button("✅ Vérifier et corriger mon montage", type="primary", use_container_width=True, key="verifier_montage_tp"):
        if not identite_complete:
            st.error("Identité incomplète : renseignez vos informations dans la barre latérale.")
        else:
            resultat = corriger_montage(tp_nom, composants_choisis, st.session_state.liaisons_etudiant)
            st.session_state.dernier_resultat = resultat
            st.session_state.historique.append({
                "Date": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "Nom": nom.strip(), "Prénom": prenom.strip(),
                "Promotion": promotion.strip(), "Groupe": groupe.strip(),
                "TP": tp_nom, "Note": resultat["note"],
                "Résultat": "Réussi" if resultat["correct"] else "À corriger",
            })
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
