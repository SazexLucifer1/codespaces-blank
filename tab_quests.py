import streamlit as st
import os
from google import genai

def render_tab(api_key, fortschritt_stufen, fortschritt, sammle_nur_kapitel_text):
    st.subheader("⚔️ Quest-Logbuch & Interaktiver Abgleich")

    QUEST_MASTER_DATEI = "quest_chronik.txt"      
    QUEST_SPIELER_DATEI = "quest_spieler_log.txt"  

    if not os.path.exists(QUEST_MASTER_DATEI):
        with open(QUEST_MASTER_DATEI, "w", encoding="utf-8") as f:
            f.write("# MASTER QUEST DATENBANK\n")
            
    if not os.path.exists(QUEST_SPIELER_DATEI):
        with open(QUEST_SPIELER_DATEI, "w", encoding="utf-8") as f:
            f.write("# AKTIVE UND BEKANNTE QUESTS DER SPIELER\n")

    if "quest_master_inhalt" not in st.session_state:
        with open(QUEST_MASTER_DATEI, "r", encoding="utf-8") as f:
            st.session_state.quest_master_inhalt = f.read()
            
    if "quest_spieler_inhalt" not in st.session_state:
        with open(QUEST_SPIELER_DATEI, "r", encoding="utf-8") as f:
            st.session_state.quest_spieler_inhalt = f.read()

    with st.expander("🛠️ Admin-Bereich: Kapitel-Quests initialisieren (Passwortgeschützt)"):
        ADMIN_PASSWORT = "pf2e"
        
        admin_eingabe = st.text_input(
            "🔑 Bitte Admin-Passwort eingeben, um den Bereich freizuschalten:", 
            type="password",
            key="pw_admin_security"
        )
        
        if admin_eingabe == ADMIN_PASSWORT:
            st.success("🔓 Admin-Zugriff gewährt.")
            st.write("Wähle ein Kapitel aus, um alle darin enthaltenen Quests vollständig in die Hintergrund-Textdatei einzulesen.")
            
            kapitel_auswahl_init = st.selectbox(
                "Welches Kapitel soll vollständig indexiert werden?",
                options=["Kapitel 1", "Kapitel 2", "Kapitel 3", "Kapitel 4"],
                key="sb_init_kapitel"
            )
            
            if st.button("🚀 Hintergrund-Initialisierung starten", key="btn_init_master"):
                kapitel_nr = fortschritt_stufen[kapitel_auswahl_init]
                kapitel_pdf_text = sammle_nur_kapitel_text(kapitel_nr)
                
                if not api_key:
                    st.error("API-Key fehlt!")
                elif not kapitel_pdf_text:
                    st.error(f"Kein passendes PDF für {kapitel_auswahl_init} im Ordner gefunden!")
                else:
                    client = genai.Client(api_key=api_key)
                    
                    init_prompt = f"""Du bist ein extrem präziser Daten-Extraktor für Pathfinder 2e.
Deine Aufgabe ist es, das Kapitel nach Quests, Meilensteinen und Story Awards zu durchsuchen.

⚠️ WICHTIGE ANWEISUNG FÜR DIE BELOHNUNGEN:
Suche im Text gezielt nach dem Signalwort "Reward:" oder "Rewards:". Kopiere den Text, die XP/XP-Awards und Gegenstände, die direkt dahinter oder in diesem Absatz stehen, eins zu eins heraus. Übersetze englische XP-Angaben (z.B. 30 XP) dabei direkt in verständliches Deutsch (z.B. 30 EP).

Erstelle für jede Quest einen Block im folgenden Format (beginne zwingend mit '### '):

### [Genauer englischer Name der Quest / des Abschnitts]
- **Kapitel**: {kapitel_nr}
- **Auftraggeber**: [Name des NPCs oder 'Erkundung/Event']
- **Ort/Region**: [Spezifischer Ort]
- **Beschreibung & Geheimnisse**: [Ausführliche Erklärung für den SL]
- **Ziel zum Abschluss**: [Was müssen die Spieler tun?]
- **Belohnung**: [Trage hier exakt die Daten ein, die im PDF hinter 'Reward:' oder 'Rewards:' stehen, übersetzt in 'EP' und deutsche Item-Namen!]"""

                    with st.spinner(f"KI analysiert {kapitel_auswahl_init} und sucht nach 'Reward:'-Blöcken..."):
                        try:
                            response = client.models.generate_content(model='gemini-2.5-flash', contents=kapitel_pdf_text + [init_prompt])
                            extraktion = response.text.strip()
                            with open(QUEST_MASTER_DATEI, "a", encoding="utf-8") as f:
                                f.write("\n\n" + extraktion)
                            with open(QUEST_MASTER_DATEI, "r", encoding="utf-8") as f:
                                st.session_state.quest_master_inhalt = f.read()
                            st.success(f"🎉 {kapitel_auswahl_init} erfolgreich mit Fokus auf 'Reward:'-Strukturen eingelesen!")
                        except Exception as e:
                            st.error(f"Fehler bei der Initialisierung: {e}")

            st.markdown("---")
            if st.checkbox("🔍 Inhalt der Master-Quest-Datenbank anzeigen", key="cb_show_master_db"):
                st.write("### 🗃️ Gesamtübersicht aller existierenden & manuellen Quests")
                
                all_admin_quests = {}
                master_bloecke = st.session_state.quest_master_inhalt.split("### ")
                for m_block in master_bloecke[1:]:
                    if m_block.strip():
                        linien = m_block.split("\n")
                        q_name = linien[0].strip()
                        attrs = {"Status": "Nicht im Spieler-Log (Rein Master)", "Spieler-Notizen": "", "Herkunft": "Master-Buch", "Belohnung": "Keine spezifische Belohnung eingetragen."}
                        for line in linien[1:]:
                            line_str = line.strip()
                            if line_str.startswith("- **Kapitel**:") or line_str.startswith("**Kapitel**:"):
                                attrs["Kapitel"] = line_str.split(":", 1)[1].strip()
                            elif line_str.startswith("- **Auftraggeber**:") or line_str.startswith("**Auftraggeber**:"):
                                attrs["Auftraggeber"] = line_str.split(":", 1)[1].strip()
                            elif line_str.startswith("- **Ort**:") or line_str.startswith("**Ort**:") or line_str.startswith("- **Ort/Region**:"):
                                attrs["Ort"] = line_str.split(":", 1)[1].strip()
                            elif line_str.startswith("- **Ziel/Aufgabe**:") or line_str.startswith("**Ziel/Aufgabe**:") or line_str.startswith("- **Beschreibung & Geheimnisse**:") or line_str.startswith("- **Ziel zum Abschluss**:"):
                                attrs["Ziel/Aufgabe"] = line_str.split(":", 1)[1].strip()
                            elif line_str.startswith("- **Belohnung**:") or line_str.startswith("**Belohnung**:"):
                                attrs["Belohnung"] = line_str.split(":", 1)[1].strip()
                        all_admin_quests[q_name] = attrs

                spieler_bloecke = st.session_state.quest_spieler_inhalt.split("### ")
                for s_block in spieler_bloecke[1:]:
                    if s_block.strip():
                        linien = s_block.split("\n")
                        q_name = linien[0].strip()
                        
                        attrs = {"Herkunft": "Spieler-Log / Manuell", "Spieler-Notizen": "", "Belohnung": "🔒 Wird nach Abschluss enthüllt"}
                        notiz_zeilen = []
                        in_notizen = False
                        
                        for line in linien[1:]:
                            line_str = line.strip()
                            if line_str.startswith("- **Kapitel**:") or line_str.startswith("**Kapitel**:"):
                                attrs["Kapitel"] = line_str.split(":", 1)[1].strip()
                            elif line_str.startswith("- **Auftraggeber**:") or line_str.startswith("**Auftraggeber**:"):
                                attrs["Auftraggeber"] = line_str.split(":", 1)[1].strip()
                            elif line_str.startswith("- **Ort**:") or line_str.startswith("**Ort**:"):
                                attrs["Ort"] = line_str.split(":", 1)[1].strip()
                            elif line_str.startswith("- **Ziel/Aufgabe**:") or line_str.startswith("**Ziel/Aufgabe**:"):
                                attrs["Ziel/Aufgabe"] = line_str.split(":", 1)[1].strip()
                            elif line_str.startswith("- **Belohnung**:") or line_str.startswith("**Belohnung**:"):
                                attrs["Belohnung"] = line_str.split(":", 1)[1].strip()
                            elif line_str.startswith("- **Status**:") or line_str.startswith("**Status**:"):
                                attrs["Status"] = line_str.split(":", 1)[1].strip()
                            elif line_str.startswith("- **Spieler-Notizen**:"):
                                in_notizen = True
                                notiz_zeilen.append(line_str.split(":", 1)[1].strip())
                            elif in_notizen:
                                notiz_zeilen.append(line)
                        
                        attrs["Spieler-Notizen"] = "\n".join(notiz_zeilen) if notiz_zeilen else ""
                        
                        if q_name in all_admin_quests:
                            all_admin_quests[q_name]["Status"] = attrs.get("Status", "Aktiv")
                            all_admin_quests[q_name]["Spieler-Notizen"] = attrs["Spieler-Notizen"]
                            all_admin_quests[q_name]["Herkunft"] = "Aus Buch (Aktiviert)"
                            if "Belohnung" in attrs and attrs["Belohnung"] != "🔒 Wird nach Abschluss enthüllt":
                                all_admin_quests[q_name]["Belohnung"] = attrs["Belohnung"]
                        else:
                            attrs["Status"] = attrs.get("Status", "Aktiv")
                            all_admin_quests[q_name] = attrs

                kap_tabs = st.tabs(["📖 Kapitel 1", "📖 Kapitel 2", "📖 Kapitel 3", "📖 Kapitel 4"])
                
                for idx, k_tab in enumerate(kap_tabs):
                    kap_nr_str = str(idx + 1)
                    with k_tab:
                        kap_quests = {k: v for k, v in all_admin_quests.items() if v.get("Kapitel") == kap_nr_str}
                        
                        if not kap_quests:
                            st.info(f"Keine Quests für Kapitel {kap_nr_str} registriert.")
                        else:
                            stat_aktiv, stat_erledigt, stat_fehl, stat_unentdeckt = st.tabs([
                                "⚔️ Aktiv", "✅ Geschafft", "❌ Fehlgeschlagen", "🔒 Unentdeckt / Inaktiv"
                            ])
                            
                            def admin_render_row(q_title, q_data, allow_activation=False):
                                h_icon = "🔒"
                                if q_data['Status'] == "Aktiv": h_icon = "⚔️"
                                elif q_data['Status'] in ["Geschafft", "Erfolgreich"]: h_icon = "✅"
                                elif q_data['Status'] == "Fehlgeschlagen": h_icon = "❌"
                                
                                with st.expander(f"{h_icon} {q_title} ({q_data['Herkunft']})"):
                                    st.markdown(f"**Auftraggeber**: {q_data.get('Auftraggeber','?')} | **Ort**: {q_data.get('Ort','?')}")
                                    st.markdown(f"**Inhalt / Ziel**: {q_data.get('Ziel/Aufgabe','?')}")
                                    st.markdown(f"🎁 **Geplante Belohnung:** {q_data.get('Belohnung','Keine Belohnung hinterlegt.')}")
                                    if q_data.get("Spieler-Notizen"):
                                        st.info(f"📝 **Spieler-Notizen:**\n{q_data['Spieler-Notizen']}")
                                    
                                    if allow_activation:
                                        st.markdown("---")
                                        if st.button(f"👁️ Für Spieler aktiv schalten", key=f"gm_act_{q_title}", use_container_width=True):
                                            ki_format = f"""### {q_title}
- **Kapitel**: {q_data.get('Kapitel')}
- **Auftraggeber**: {q_data.get('Auftraggeber', 'Unbekannt')}
- **Ort**: {q_data.get('Ort', 'Unbekannt')}
- **Ziel/Aufgabe**: {q_data.get('Ziel/Aufgabe', 'Vom Game Master freigeschaltet.')}
- **Belohnung**: {q_data.get('Belohnung', 'Keine Belohnung gefunden.')}
- **Status**: Aktiv
- **Spieler-Notizen**: Vom Spielleiter manuell aufgedeckt."""
                                            
                                            aktueller_log_text = st.session_state.quest_spieler_inhalt.strip()
                                            neuer_spieler_log = aktueller_log_text + "\n\n" + ki_format
                                            
                                            with open(QUEST_SPIELER_DATEI, "w", encoding="utf-8") as f:
                                                f.write(neuer_spieler_log)
                                                
                                            st.session_state.quest_spieler_inhalt = neuer_spieler_log
                                            st.success(f"🎉 '{q_title}' wurde im Logbuch der Spieler aktiviert!")
                                            st.rerun()

                            with stat_aktiv:
                                f_quests = {k: v for k, v in kap_quests.items() if v.get("Status") == "Aktiv"}
                                if not f_quests: st.info("Keine aktiven Quests in diesem Kapitel.")
                                for name, daten in f_quests.items(): admin_render_row(name, daten)
                                
                            with stat_erledigt:
                                f_quests = {k: v for k, v in kap_quests.items() if v.get("Status") in ["Geschafft", "Erfolgreich"]}
                                if not f_quests: st.info("Keine abgeschlossenen Quests in diesem Kapitel.")
                                for name, daten in f_quests.items(): admin_render_row(name, daten)
                                
                            with stat_fehl:
                                f_quests = {k: v for k, v in kap_quests.items() if v.get("Status") == "Fehlgeschlagen"}
                                if not f_quests: st.info("Keine fehlgeschlagenen Quests.")
                                for name, daten in f_quests.items(): admin_render_row(name, daten)
                                
                            with stat_unentdeckt:
                                f_quests = {k: v for k, v in kap_quests.items() if "Nicht im Spieler-Log" in v.get("Status", "")}
                                if not f_quests: st.info("Alle Quests dieses Kapitels wurden von den Spielern bereits entdeckt!")
                                for name, daten in f_quests.items(): admin_render_row(name, daten, allow_activation=True)
        
        elif admin_eingabe.strip() != "":
            st.error("❌ Falsches Passwort! Zugriff verweigert.")

    st.write("### 📥 Neue Quest im Logbuch freischalten")
    
    @st.dialog("➕ Manuelle Quest erstellen")
    def manuelle_quest_popup(initial_text, kapitel_nr):
        st.write("Fülle die Details für die manuelle Quest aus:")
        standard_titel = initial_text[:30].strip() + "..." if len(initial_text) > 30 else initial_text.strip()
        
        q_titel = st.text_input("Quest-Name:", value=standard_titel if initial_text else "Eigene Aufgabe")
        q_geber = st.text_input("Auftraggeber:", placeholder="z.B. Maku, Dorfältester, Unbekannt")
        q_ort = st.text_input("Ort / Region:", placeholder="z.B. Am Fluss, Pharasmas Tempel")
        q_ziel = st.text_area("Hauptziel / Aufgabe:", value=initial_text, placeholder="Was exakt müsst ihr tun?")
        q_belohnung = st.text_input("🎁 EP & Items (Belohnung):", placeholder="z.B. 40 EP, +1 Langbogen")
        
        if st.button("💾 Quest definitiv anlegen", use_container_width=True):
            if not q_titel.strip() or not q_ziel.strip():
                st.error("Bitte gib mindestens einen Namen und ein Ziel an!")
            else:
                manuelle_quest = f"""### {q_titel.strip()}
- **Kapitel**: {kapitel_nr}
- **Auftraggeber**: {q_geber.strip() if q_geber.strip() else 'Unbekannt'}
- **Ort**: {q_ort.strip() if q_ort.strip() else 'Aktueller Ort'}
- **Ziel/Aufgabe**: {q_ziel.strip()}
- **Belohnung**: {q_belohnung.strip() if q_belohnung.strip() else 'Keine Belohnung angegeben.'}
- **Status**: Aktiv
- **Spieler-Notizen**: Von Spielern manuell eingetragen."""
                
                aktueller_inhalt = ""
                if os.path.exists(QUEST_SPIELER_DATEI):
                    with open(QUEST_SPIELER_DATEI, "r", encoding="utf-8") as f:
                        aktueller_inhalt = f.read().strip()
                
                neuer_spieler_log = blackjack = blackjack = aktueller_inhalt + "\n\n" + manuelle_quest
                with open(QUEST_SPIELER_DATEI, "w", encoding="utf-8") as f:
                    f.write(neuer_spieler_log)
                
                st.session_state.quest_spieler_inhalt = neuer_spieler_log
                st.rerun()

    spieler_kapitel_auswahl = st.selectbox(
        "In welchem Kapitel habt ihr diese Quest erhalten?",
        options=["Kapitel 1", "Kapitel 2", "Kapitel 3", "Kapitel 4"],
        key="sb_spieler_kapitel"
    )
    spieler_eingabe = st.text_area(
        "Was ist passiert? Beschreibe in eigenen Worten, welche Quest oder Aufgabe ihr erhalten habt:",
        placeholder="z.B. Ein alter Mann am Fluss namens Maku hat uns gebeten, nach seiner vermissten Tochter zu suchen...",
        key="ta_spieler_eingabe"
    )

    col_ki, col_manuell = st.columns(2)

    with col_ki:
        if st.button("⚔️ Quest automatisch abgleichen", key="btn_match_quest", use_container_width=True):
            gesuchtes_kapitel_nr = fortschritt_stufen[spieler_kapitel_auswahl]
            if not api_key:
                st.error("API-Key fehlt!")
            elif not spieler_eingabe.strip():
                st.warning("Bitte gib zuerst ein, was die Gruppe erlebt hat!")
            elif len(st.session_state.quest_master_inhalt.strip()) < 50:
                st.error("Die Master-Datenbank ist leer! Bitte initialisiere zuerst ein Kapitel oben.")
            else:
                client = genai.Client(api_key=api_key)
                abgleich_prompt = f"""Du bist das Gehirn eines Pen-&-Paper-Logbuchs. Dir liegt eine Master-Datenbank aller existierenden Quests vor.
WICHTIG: Die Spieler haben angegeben, dass diese Quest aus **Kapitel {gesuchtes_kapitel_nr}** stammt.

Hier ist die Master-Datenbank aller Quests:
{st.session_state.quest_master_inhalt}

Hier ist die Beschreibung der Spieler:
"{spieler_eingabe}"

Aufgabe:
1. Finde die passendste Quest aus Kapitel {gesuchtes_kapitel_nr}.
2. Bereite sie absolut SPOILERFREI auf DEUTSCH auf!
3. Extrahiere die Zeile "- **Belohnung**:" exakt so, wie sie in der Master-Datenbank steht. 
⚠️ WICHTIG: Die Belohnung wurde im Master-File aus dem Textfeld hinter 'Reward:' generiert. Achte darauf, dass hier die EP (Erfahrungspunkte) und Items lückenlos und sauber aufgeführt werden!

Formatierung der Ausgabe (EXAKT so einhalten!):
### [Hier der exakte Quest-Name aus der Master-Datenbank]
- **Kapitel**: {gesuchtes_kapitel_nr}
- **Auftraggeber**: [Auftraggeber]
- **Ort**: [Ort]
- **Ziel/Aufgabe**: [Spoilerfreies Ziel]
- **Belohnung**: [Die Belohnung aus der Masterdatenbank mit klaren Werten wie '40 EP', Gegenständen etc.]
- **Status**: Aktiv
- **Spieler-Notizen**: Quest freigeschaltet.

Wenn absolut kein Treffer, antworte NUR mit: KEIN_TREFFER"""

                with st.spinner(f"Gemini sucht in Kapitel {gesuchtes_kapitel_nr}..."):
                    try:
                        response = client.models.generate_content(model='gemini-2.5-flash', contents=[abgleich_prompt])
                        ki_antwort = response.text.strip()
                        
                        if "KEIN_TREFFER" in ki_antwort:
                            st.error(f"❌ Keine passende Quest in {spieler_kapitel_auswahl} gefunden.")
                        else:
                            quest_titel = ki_antwort.split("\n")[0].replace("### ", "").strip()
                            if quest_titel in st.session_state.quest_spieler_inhalt:
                                st.warning(f"ℹ️ '{quest_titel}' ist bereits im Logbuch!")
                            else:
                                neuer_spieler_log = st.session_state.quest_spieler_inhalt.strip() + "\n\n" + ki_antwort
                                with open(QUEST_SPIELER_DATEI, "w", encoding="utf-8") as f:
                                    f.write(neuer_spieler_log)
                                st.session_state.quest_spieler_inhalt = neuer_spieler_log
                                st.success(f"🎉 '{quest_titel}' freigeschaltet!")
                                st.rerun()
                    except Exception as e:
                        st.error(f"Fehler: {e}")

    with col_manuell:
        if st.button("➕ Quest manuell eintragen...", key="btn_manual_quest", use_container_width=True):
            st.session_state.trigger_manual_popup = True

    if st.session_state.get("trigger_manual_popup", False):
        st.session_state.trigger_manual_popup = False 
        gesuchtes_kapitel_nr = fortschritt_stufen[spieler_kapitel_auswahl]
        text_fuer_popup = spieler_eingabe.strip()
        manuelle_quest_popup(text_fuer_popup, gesuchtes_kapitel_nr)

    def speichere_spieler_logbuch(aktive_liste):
        neuer_text = "# AKTIVE UND BEKANNTE QUESTS DER SPIELER"
        for q_title, q_attr in aktive_liste.items():
            neuer_text += f"\n\n### {q_title}\n"
            neuer_text += f"- **Kapitel**: {q_attr.get('Kapitel', '?')}\n"
            neuer_text += f"- **Auftraggeber**: {q_attr.get('Auftraggeber', '?')}\n"
            neuer_text += f"- **Ort**: {q_attr.get('Ort', '?')}\n"
            neuer_text += f"- **Ziel/Aufgabe**: {q_attr.get('Ziel/Aufgabe', '?')}\n"
            neuer_text += f"- **Belohnung**: {q_attr.get('Belohnung', 'Keine Belohnung.')}\n"
            neuer_text += f"- **Status**: {q_attr.get('Status', 'Aktiv')}\n"
            notiz_text = q_attr.get('Spieler-Notizen', '').strip()
            neuer_text += f"- **Spieler-Notizen**: {notiz_text if notiz_text else 'Keine Notizen vorhanden.'}"
        
        with open(QUEST_SPIELER_DATEI, "w", encoding="utf-8") as f:
            f.write(neuer_text)
        st.session_state.quest_spieler_inhalt = neuer_text

    st.write("### 📜 Euer Quest-Logbuch")
    
    @st.dialog("⚠️ Quest endgültig löschen?")
    def loesch_sicherheits_popup(quest_name, aktive_liste):
        st.warning(f"Bist du sicher, dass du die Quest **'{quest_name}'** unwiderruflich löschen möchtest?")
        st.write("Diese Aktion kann nicht rückgängig gemacht werden.")
        col_ja, col_nein = st.columns(2)
        with col_ja:
            if st.button("🔴 Ja, endgültig löschen", use_container_width=True, key=f"confirm_del_{quest_name}"):
                if quest_name in aktive_liste:
                    del aktive_liste[quest_name]
                    speichere_spieler_logbuch(parsed_quests)
                    st.rerun()
        with col_nein:
            if st.button("Abbrechen", use_container_width=True, key=f"cancel_del_{quest_name}"):
                st.rerun()

    spieler_quest_bloecke = st.session_state.quest_spieler_inhalt.split("### ")
    parsed_quests = {}
    
    for s_block in spieler_quest_bloecke[1:]:
        if s_block.strip():
            linien = s_block.split("\n")
            q_name = linien[0].strip()
            
            attrs = {"Belohnung": "Keine Belohnung."}
            notiz_zeilen = []
            in_notizen = False
            
            for line in linien[1:]:
                line_str = line.strip()
                if line_str.startswith("- **Kapitel**:") or line_str.startswith("**Kapitel**:"):
                    attrs["Kapitel"] = line_str.split(":", 1)[1].strip()
                elif line_str.startswith("- **Auftraggeber**:") or line_str.startswith("**Auftraggeber**:"):
                    attrs["Auftraggeber"] = line_str.split(":", 1)[1].strip()
                elif line_str.startswith("- **Ort**:") or line_str.startswith("**Ort**:"):
                    attrs["Ort"] = line_str.split(":", 1)[1].strip()
                elif line_str.startswith("- **Ziel/Aufgabe**:") or line_str.startswith("**Ziel/Aufgabe**:"):
                    attrs["Ziel/Aufgabe"] = line_str.split(":", 1)[1].strip()
                elif line_str.startswith("- **Belohnung**:") or line_str.startswith("**Belohnung**:"):
                    attrs["Belohnung"] = line_str.split(":", 1)[1].strip()
                elif line_str.startswith("- **Status**:") or line_str.startswith("**Status**:"):
                    attrs["Status"] = line_str.split(":", 1)[1].strip()
                elif line_str.startswith("- **Spieler-Notizen**:"):
                    in_notizen = True
                    notiz_zeilen.append(line_str.split(":", 1)[1].strip())
                elif in_notizen:
                    notiz_zeilen.append(line)
            
            attrs["Spieler-Notizen"] = "\n".join(notiz_zeilen) if notiz_zeilen else ""
            parsed_quests[q_name] = attrs

    if "quest_to_delete" in st.session_state:
        q_del_target = st.session_state.pop("quest_to_delete")
        loesch_sicherheits_popup(q_del_target, parsed_quests)

    if not parsed_quests:
        st.info("Euer Logbuch ist noch leer. Aktiviert oben eure erste Aufgabe!")
    else:
        sub_tab_aktiv, sub_tab_geschafft, sub_tab_fehlgeschlagen = st.tabs([
            "⚔️ Aktiv", "✅ Geschafft", "❌ Fehlgeschlagen"
        ])
        
        def render_quest_eintrag(name, daten):
            status = daten.get("Status", "Aktiv")
            icon = "⚔️"
            is_done = status in ["Geschafft", "Erfolgreich"]
            if is_done: icon = "✅"
            elif status == "Fehlgeschlagen": icon = "❌"
                
            with st.expander(f"{icon} {name} (Kapitel {daten.get('Kapitel', '?')})"):
                st.markdown(f"**Auftraggeber**: {daten.get('Auftraggeber', '?')} | **Ort**: {daten.get('Ort', '?')}")
                st.markdown(f"**Hauptziel**: {daten.get('Ziel/Aufgabe', '?')}")
                
                st.write("---")
                if is_done:
                    st.markdown(f"🎁 **Freigeschaltete Belohnung (EP & Loot):**\n`{daten.get('Belohnung', 'Keine eingetragen.')}`")
                else:
                    st.markdown("🎁 **Belohnung (EP & Loot):**\n*🔒 Wird erst nach erfolgreichem Quest-Abschluss enthüllt!*")
                st.write("---")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button("⚔️ Aktiv setzen", key=f"btn_akt_{name}"):
                        parsed_quests[name]["Status"] = "Aktiv"
                        speichere_spieler_logbuch(parsed_quests)
                        st.rerun()
                with col2:
                    if st.button("✅ Auf Geschafft", key=f"btn_ges_{name}"):
                        parsed_quests[name]["Status"] = "Geschafft"
                        speichere_spieler_logbuch(parsed_quests)
                        st.rerun()
                with col3:
                    if st.button("❌ Fehlgeschlagen", key=f"btn_fail_{name}"):
                        parsed_quests[name]["Status"] = "Fehlgeschlagen"
                        speichere_spieler_logbuch(parsed_quests)
                        st.rerun()
                
                st.markdown("---")
                
                alte_notiz = daten.get("Spieler-Notizen", "").replace("Keine Notizen vorhanden.", "").strip()
                neue_notiz = st.text_area(
                    "📝 Eigene Notizen der Gruppe editieren:",
                    value=alte_notiz,
                    placeholder="z.B. Wir haben herausgefunden, dass...",
                    key=f"ta_notiz_{name}"
                )
                
                col_save, col_del = st.columns([3, 1])
                with col_save:
                    if st.button("💾 Notizen speichern", key=f"btn_save_{name}", use_container_width=True):
                        parsed_quests[name]["Spieler-Notizen"] = neue_notiz
                        speichere_spieler_logbuch(parsed_quests)
                        st.success("Notiz erfolgreich aktualisiert!")
                        st.rerun()
                        
                with col_del:
                    if st.button("🗑️ Quest löschen", key=f"btn_del_{name}", use_container_width=True, type="secondary"):
                        st.session_state.quest_to_delete = name
                        st.rerun()

        with sub_tab_aktiv:
            aktive_quests = {k: v for k, v in parsed_quests.items() if v.get("Status", "Aktiv") == "Aktiv"}
            if not aktive_quests: st.info("Aktuell keine aktiven Quests.")
            for name, daten in aktive_quests.items(): render_quest_eintrag(name, daten)
                    
        with sub_tab_geschafft:
            geschaffte_quests = {k: v for k, v in parsed_quests.items() if v.get("Status") in ["Geschafft", "Erfolgreich"]}
            if not geschaffte_quests: st.info("Noch keine Quests abgeschlossen.")
            for name, daten in geschaffte_quests.items(): render_quest_eintrag(name, daten)
                    
        with sub_tab_fehlgeschlagen:
            fehlgeschlagene_quests = {k: v for k, v in parsed_quests.items() if v.get("Status") == "Fehlgeschlagen"}
            if not fehlgeschlagene_quests: st.info("Glücklicherweise noch keine Quests fehlgeschlagen!")
            for name, daten in fehlgeschlagene_quests.items(): render_quest_eintrag(name, daten)