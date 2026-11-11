def laboratoire_enseignant_interactif():
    """Laboratoire virtuel enseignant : générateur de TP, appareils, simulation, mesures et corrigé."""

    st.divider()
    st.header("🧪 Laboratoire virtuel enseignant")
    st.caption(
        "Générateur de TP, commandes d'appareils, simulation, mesures numériques, "
        "oscilloscope virtuel et corrigé confidentiel."
    )

    onglets = st.tabs([
        "1. Générateur de TP",
        "2. Simulation et mesures",
        "3. Oscilloscope virtuel",
        "4. Corrigé confidentiel",
    ])

    # ------------------------------------------------------------------
    # 1. Générateur de TP
    # ------------------------------------------------------------------
    with onglets[0]:

        col_tp, col_marque = st.columns([3, 2])

        with col_tp:
            tp_lab = st.selectbox(
                "Sélectionner le TP",
                list(TPS.keys()),
                key="lab_tp_selection"
            )

        with col_marque:
            marque_lab = st.selectbox(
                "Marque des composants",
                list(MARQUES_COMPOSANTS.keys()),
                key="lab_marque"
            )

        tp_data = TPS[tp_lab]
        st.info(tp_data["description"])

        composants_possibles = sorted(
            {composant for elements in COMPOSANTS.values() for composant in elements}
        )

        composants_lab = st.multiselect(
            "Composants du montage",
            composants_possibles,
            default=[
                composant
                for composant in tp_data["composants"]
                if composant in composants_possibles
            ],
            key="lab_composants"
        )

        st.subheader("Paramètres électriques et mécaniques")

        c1, c2, c3, c4 = st.columns(4)

        with c1:
            u_lab = st.slider(
                "Tension d'alimentation U (V)",
                0.0,
                600.0,
                24.0,
                0.5,
                key="lab_u"
            )

        with c2:
            f_lab = st.slider(
                "Fréquence f (Hz)",
                0.0,
                400.0,
                50.0,
                0.5,
                key="lab_f"
            )

        with c3:
            r_lab = st.slider(
                "Résistance R (Ω)",
                0.1,
                10000.0,
                100.0,
                0.1,
                key="lab_r"
            )

        with c4:
            c_lab = st.slider(
                "Capacité C (µF)",
                0.0,
                10000.0,
                100.0,
                1.0,
                key="lab_c"
            )

        c5, c6, c7, c8 = st.columns(4)

        with c5:
            l_lab = st.slider(
                "Inductance L (mH)",
                0.0,
                5000.0,
                100.0,
                1.0,
                key="lab_l"
            )

        with c6:
            couple_lab = st.slider(
                "Couple de charge (N·m)",
                0.0,
                200.0,
                10.0,
                0.5,
                key="lab_couple"
            )

        with c7:
            vitesse_lab = st.slider(
                "Vitesse moteur (tr/min)",
                0.0,
                6000.0,
                1450.0,
                10.0,
                key="lab_vitesse"
            )

        with c8:
            pot_lab = st.slider(
                "Potentiomètre (%)",
                0.0,
                100.0,
                50.0,
                1.0,
                key="lab_pot"
            )

        st.subheader("Commandes des appareils de laboratoire")

        col_v, col_a, col_m = st.columns(3)

        with col_v:
            st.markdown("**Voltmètre**")

            calibre_v = st.select_slider(
                "Calibre",
                ["200 mV", "2 V", "20 V", "200 V", "600 V"],
                value="200 V",
                key="lab_cal_v"
            )

            mode_v = st.radio(
                "Mode",
                ["DC", "AC"],
                horizontal=True,
                key="lab_mode_v"
            )

        with col_a:
            st.markdown("**Ampèremètre**")

            calibre_a = st.select_slider(
                "Calibre",
                ["200 µA", "2 mA", "20 mA", "200 mA", "2 A", "10 A", "20 A"],
                value="10 A",
                key="lab_cal_a"
            )

            mode_a = st.radio(
                "Mode",
                ["DC", "AC"],
                horizontal=True,
                key="lab_mode_a"
            )

        with col_m:
            st.markdown("**Multimètre**")

            fonction_m = st.selectbox(
                "Fonction",
                [
                    "Tension DC",
                    "Tension AC",
                    "Courant DC",
                    "Courant AC",
                    "Résistance",
                    "Continuité",
                    "Fréquence"
                ],
                key="lab_fonction_m"
            )

            calibre_m = st.select_slider(
                "Calibre",
                [
                    "Auto",
                    "200 mV",
                    "2 V",
                    "20 V",
                    "200 V",
                    "600 V",
                    "2 mA",
                    "200 mA",
                    "10 A",
                    "2 kΩ",
                    "2 MΩ"
                ],
                value="Auto",
                key="lab_cal_m"
            )

        col_alim, col_mot, col_pot = st.columns(3)

        with col_alim:
            st.markdown("**Alimentation de laboratoire**")

            u_alim = st.slider(
                "Tension de sortie (V)",
                0.0,
                60.0,
                12.0,
                0.1,
                key="lab_alim_u"
            )

            i_max = st.slider(
                "Limitation de courant (A)",
                0.0,
                10.0,
                2.0,
                0.05,
                key="lab_alim_imax"
            )

        with col_mot:
            st.markdown("**Moteur**")

            couple_moteur = st.slider(
                "Couple mécanique demandé (N·m)",
                0.0,
                200.0,
                10.0,
                0.5,
                key="lab_mot_couple"
            )

            vitesse_moteur = st.slider(
                "Consigne de vitesse (tr/min)",
                0.0,
                6000.0,
                1450.0,
                10.0,
                key="lab_mot_vitesse"
            )

        with col_pot:
            st.markdown("**Potentiomètre**")

            valeur_pot = st.slider(
                "Position du curseur (%)",
                0.0,
                100.0,
                50.0,
                1.0,
                key="lab_pot_curseur"
            )

            st.caption(
                f"Résistance entre curseur et borne A : "
                f"{valeur_pot / 100 * 1000:.0f} Ω pour un potentiomètre de 1 kΩ."
            )

    # ------------------------------------------------------------------
    # 2. Simulation et mesures
    # ------------------------------------------------------------------
    with onglets[1]:

        st.subheader("Simulation du montage")
        st.caption(
            "Les résultats sont recalculés à partir du TP, des composants "
            "et des réglages des appareils."
        )

        if st.button(
            "▶️ Lancer le calcul du fonctionnement du montage",
            type="primary",
            use_container_width=True,
            key="lab_lancer_simulation"
        ):
            st.session_state["lab_resultats"] = {
                "tp": tp_lab,
                "u": u_lab,
                "f": f_lab,
                "r": r_lab,
                "c": c_lab * 1e-6,
                "l": l_lab * 1e-3,
                "couple": couple_lab,
                "vitesse": vitesse_lab,
                "u_alim": u_alim,
                "i_max": i_max,
                "pot": valeur_pot
            }

        resultats = st.session_state.get("lab_resultats")

        if resultats is None:
            st.info("Réglez les paramètres puis lancez la simulation.")

        else:
            u = resultats["u"]
            f = resultats["f"]
            r = max(resultats["r"], 1e-6)
            c = resultats["c"]
            l = resultats["l"]

            if "Graetz" in resultats["tp"] or "Redressement" in resultats["tp"]:

                v_moy = 0.9 * u
                i_moy = v_moy / r
                p = v_moy * i_moy

                grandeurs = {
                    "Tension moyenne DC": (v_moy, "V"),
                    "Courant moyen DC": (i_moy, "A"),
                    "Puissance DC": (p, "W"),
                    "Fréquence d'ondulation": (2 * f, "Hz")
                }

            elif "RC" in resultats["tp"]:

                tau = r * c
                v_final = u
                i_initial = u / r

                grandeurs = {
                    "Constante de temps τ": (tau, "s"),
                    "Tension finale du condensateur": (v_final, "V"),
                    "Courant initial": (i_initial, "A"),
                    "Fréquence": (f, "Hz")
                }

            elif "Arduino" in resultats["tp"]:

                v_led = 2.0
                i_led = max(0.0, (u - v_led) / r) * 1000

                grandeurs = {
                    "Courant LED": (i_led, "mA"),
                    "Tension résistance": (max(0.0, u - v_led), "V"),
                    "Puissance résistance": (
                        max(0.0, u - v_led) ** 2 / r * 1000,
                        "mW"
                    )
                }

            elif "moteur asynchrone" in resultats["tp"].lower():

                p_utile = max(
                    0.05,
                    couple_moteur * vitesse_moteur * 2 * math.pi / 60 / 1000
                )

                rendement = 0.86
                cos_phi = 0.82

                p_absorbee = p_utile / rendement
                s = p_absorbee / cos_phi
                i_ligne = s * 1000 / (math.sqrt(3) * max(u, 1.0))
                couple = 9550 * p_utile / max(vitesse_moteur, 1.0)

                grandeurs = {
                    "Puissance utile": (p_utile, "kW"),
                    "Puissance absorbée": (p_absorbee, "kW"),
                    "Courant de ligne": (i_ligne, "A"),
                    "Couple": (couple, "N·m"),
                    "Vitesse": (vitesse_moteur, "tr/min"),
                    "Rendement": (rendement * 100, "%"),
                    "Fréquence": (f, "Hz")
                }

            else:

                i_dc = u / r
                p_dc = u * i_dc

                grandeurs = {
                    "Tension": (u, "V"),
                    "Courant": (i_dc, "A"),
                    "Puissance": (p_dc, "W"),
                    "Résistance": (r, "Ω"),
                    "Fréquence": (f, "Hz")
                }

            grandeurs["Tension"] = (u, "V")
            grandeurs["Courant"] = (
                grandeurs.get(
                    "Courant moyen DC",
                    grandeurs.get(
                        "Courant initial",
                        grandeurs.get("Courant de ligne", (0.0, "A"))
                    )
                )[0],
                "A"
            )

            grandeurs["Puissance"] = (
                grandeurs.get(
                    "Puissance DC",
                    grandeurs.get("Puissance absorbée", (0.0, "W"))
                )[0],
                "W"
            )

            grandeurs["Fréquence"] = (f, "Hz")
            grandeurs["Vitesse"] = (vitesse_moteur, "tr/min")
            grandeurs["Couple"] = (couple_moteur, "N·m")
            grandeurs["Rendement"] = (
                grandeurs.get("Rendement", (0.0, "%"))[0],
                "%"
            )

            st.subheader("Mesures numériques")

            choix_mesure = st.selectbox(
                "Grandeur à afficher",
                [
                    "Tension",
                    "Courant",
                    "Puissance",
                    "Fréquence",
                    "Vitesse",
                    "Couple",
                    "Rendement",
                    "Constante de temps τ",
                    "Tension moyenne DC",
                    "Courant moyen DC",
                    "Courant LED"
                ],
                key="lab_grandeur_mesuree"
            )

            if choix_mesure in grandeurs:

                valeur, unite = grandeurs[choix_mesure]

                calibres = {
                    "V": ["200 mV", "2 V", "20 V", "200 V", "600 V"],
                    "A": [
                        "200 µA",
                        "2 mA",
                        "20 mA",
                        "200 mA",
                        "2 A",
                        "10 A",
                        "20 A"
                    ]
                }

                facteurs = {
                    "mV": 1e-3,
                    "V": 1.0,
                    "µA": 1e-6,
                    "mA": 1e-3,
                    "A": 1.0
                }

                if unite in calibres:
                    calibre_actif = calibre_v if unite == "V" else calibre_a
                    nombre, prefixe = calibre_actif.split()
                    limite = float(nombre) * facteurs[prefixe]
                    depassement = abs(valeur) > limite
                else:
                    calibre_actif = "Automatique"
                    depassement = False

                col_res1, col_res2 = st.columns([1, 2])

                with col_res1:
                    if depassement:
                        st.error("OL — dépassement de calibre")
                    else:
                        st.metric(
                            choix_mesure,
                            f"{valeur:.3g} {unite}"
                        )

                with col_res2:
                    st.caption(
                        f"Calibre actif : {calibre_actif} — "
                        f"mode {mode_v if unite == 'V' else mode_a}"
                    )

            else:
                st.warning(
                    "Cette grandeur n'est pas disponible pour le TP sélectionné."
                )

            st.subheader("Résultats calculés")

            lignes = []

            for nom_grandeur, (valeur, unite) in grandeurs.items():
                lignes.append(
                    {
                        "Grandeur": nom_grandeur,
                        "Valeur": f"{valeur:.4g}",
                        "Unité": unite
                    }
                )

            st.dataframe(
                pd.DataFrame(lignes),
                use_container_width=True,
                hide_index=True
            )

            courant_calcule = grandeurs.get("Courant", (0.0, "A"))[0]

            if resultats["i_max"] > 0 and courant_calcule > resultats["i_max"]:
                st.warning(
                    "⚠️ Limitation de courant de l'alimentation atteinte : "
                    "réduisez la tension ou augmentez la limite."
                )

    # ------------------------------------------------------------------
    # 3. Oscilloscope virtuel
    # ------------------------------------------------------------------
    with onglets[2]:

        st.subheader("Oscilloscope virtuel")

        col_o1, col_o2, col_o3, col_o4 = st.columns(4)

        with col_o1:
            canal = st.selectbox(
                "Canal affiché",
                [
                    "CH1 — Tension",
                    "CH2 — Courant",
                    "CH1 + CH2"
                ],
                key="lab_osc_canal"
            )

            v_div = st.select_slider(
                "V/div",
                [
                    "50 mV",
                    "100 mV",
                    "200 mV",
                    "500 mV",
                    "1 V",
                    "2 V",
                    "5 V",
                    "10 V",
                    "20 V",
                    "50 V",
                    "100 V"
                ],
                value="10 V",
                key="lab_osc_vdiv"
            )

        with col_o2:
            t_div = st.select_slider(
                "s/div",
                [
                    "100 µs",
                    "200 µs",
                    "500 µs",
                    "1 ms",
                    "2 ms",
                    "5 ms",
                    "10 ms",
                    "20 ms",
                    "50 ms"
                ],
                value="5 ms",
                key="lab_osc_tdiv"
            )

            couplage = st.radio(
                "Couplage",
                ["DC", "AC"],
                horizontal=True,
                key="lab_osc_couplage"
            )

        with col_o3:
            declenchement = st.slider(
                "Niveau de déclenchement (V)",
                -300.0,
                300.0,
                0.0,
                0.5,
                key="lab_osc_trigger"
            )

            pente = st.selectbox(
                "Pente",
                ["Montante", "Descendante"],
                key="lab_osc_pente"
            )

        with col_o4:
            curseur1 = st.slider(
                "Curseur 1 (ms)",
                0.0,
                100.0,
                20.0,
                0.5,
                key="lab_osc_curseur1"
            )

            curseur2 = st.slider(
                "Curseur 2 (ms)",
                0.0,
                100.0,
                60.0,
                0.5,
                key="lab_osc_curseur2"
            )

        if st.button(
            "Actualiser l'oscilloscope",
            type="primary",
            use_container_width=True,
            key="lab_osc_actualiser"
        ):
            st.session_state["lab_osc_actif"] = True

        if st.session_state.get("lab_osc_actif"):

            if mode_v == "AC":
                amplitude = u_lab / math.sqrt(2)
                t = np.linspace(0, 10 / max(f_lab, 0.1), 2000)
                ch1 = amplitude * np.sin(2 * math.pi * f_lab * t)
                ch2 = amplitude / r_lab * np.sin(2 * math.pi * f_lab * t)

            else:
                amplitude = u_lab / 2
                t = np.linspace(0, 0.1, 2000)
                ch1 = np.full_like(t, u_lab)
                ch2 = np.full_like(t, u_lab / r_lab)

            if couplage == "AC":
                ch1 = ch1 - np.mean(ch1)
                ch2 = ch2 - np.mean(ch2)

            fig = go.Figure()

            if "CH1" in canal:
                fig.add_trace(
                    go.Scatter(
                        x=t * 1000,
                        y=ch1,
                        name="CH1 — Tension",
                        line=dict(color="#2563eb", width=2)
                    )
                )

            if "CH2" in canal:
                fig.add_trace(
                    go.Scatter(
                        x=t * 1000,
                        y=ch2,
                        name="CH2 — Courant",
                        line=dict(color="#dc2626", width=2),
                        yaxis="y2"
                    )
                )

            fig.add_hline(
                y=declenchement,
                line_dash="dash",
                line_color="green",
                annotation_text="Trigger"
            )

            fig.add_vline(
                x=curseur1,
                line_dash="dot",
                line_color="orange",
                annotation_text="Curseur 1"
            )

            fig.add_vline(
                x=curseur2,
                line_dash="dot",
                line_color="purple",
                annotation_text="Curseur 2"
            )

            fig.update_layout(
                title=f"Oscilloscope — {v_div}/div, {t_div}/div, couplage {couplage}",
                xaxis_title="Temps (ms)",
                yaxis_title="Tension (V)",
                yaxis2=dict(
                    title="Courant (A)",
                    overlaying="y",
                    side="right",
                    showgrid=False
                ),
                height=430,
                margin=dict(l=10, r=10, t=45, b=10)
            )

            st.plotly_chart(
                fig,
                use_container_width=True,
                key="lab_oscilloscope"
            )

            st.caption(
                f"Fenêtre affichée : 10 divisions × {t_div}. "
                f"Résolution verticale : {v_div}/div."
            )

        else:
            st.info(
                "Cliquez sur « Actualiser l'oscilloscope » pour tracer les signaux."
            )

    # ------------------------------------------------------------------
    # 4. Corrigé confidentiel
    # ------------------------------------------------------------------
    with onglets[3]:

        st.subheader("🔒 Corrigé confidentiel")
        st.caption(
            "Le schéma câblé de référence et la liste des liaisons sont accessibles "
            "uniquement après confirmation du mot de passe enseignant."
        )

        mot_de_passe_corrige = st.text_input(
            "Mot de passe du corrigé",
            type="password",
            key="lab_mdp_corrige"
        )

        if st.button(
            "Afficher le corrigé",
            type="primary",
            use_container_width=True,
            key="lab_afficher_corrige"
        ):
            cle = obtenir_mot_de_passe_enseignant()

            if cle and hmac.compare_digest(mot_de_passe_corrige, cle):
                st.session_state["lab_corrige_autorise"] = True
            else:
                st.error("Mot de passe incorrect.")
                st.session_state["lab_corrige_autorise"] = False

        if st.session_state.get("lab_corrige_autorise"):

            st.success("Accès au corrigé autorisé.")

            st.plotly_chart(
                creer_schema_tp(tp_lab),
                use_container_width=True,
                key="lab_schema_corrige"
            )

            liaisons = tp_data.get("liaisons", [])

            if liaisons:
                st.dataframe(
                    pd.DataFrame(
                        [
                            {
                                "Borne de départ": a,
                                "Borne d'arrivée": b
                            }
                            for a, b in liaisons
                        ]
                    ),
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info(
                    "Aucune liaison de référence n'est enregistrée pour ce TP."
                )

        else:
            st.info(
                "Entrez le mot de passe enseignant pour consulter "
                "le schéma câblé de référence."
            )


def ajouter_appel_laboratoire_enseignant():
    """Ajoute l'appel du laboratoire dans l'espace enseignant."""
    return """
    laboratoire_enseignant_interactif()
    st.divider()
"""

