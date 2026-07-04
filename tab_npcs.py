import streamlit as st
import os
import re
from google import genai

def render_tab(api_key, fortschritt_stufen, fortschritt, sammle_kampagnen_texte, sammle_nur_kapitel_text):
    st.subheader("👤 NPC-Chronik & Dorfverwaltung")

    NPC_DATEI = "npc_chronik.txt"
    BILDER_ORDNER = "npc_bilder"
    
    if not os.path.exists(BILDER_ORDNER):
        os.makedirs(BILDER_ORDNER)

    if not os.path.exists(NPC_DATEI):
        with open(NPC_DATEI, "w", encoding="utf-8") as f:
            f.write("# BEKANNTE NPCs IN WILLOWSHORE\n\n*Hier werden alle NPCs automatisch gesammelt und aktualisiert.*\n")
        st.session_state.npc_inhalt = "# BEKANNTE NPCs IN WILLOWSHORE\n\n*Hier werden alle NPCs automatisch gesammelt und aktualisiert.*\n"

    if "npc_inhalt" not in st.session_state:
        with open(NPC_DATEI, "r", encoding="utf-8") as f:
            st.session_state.npc_inhalt = f.read()

    # --- GAMEMASTER REGULIERUNG ---
    st.sidebar.markdown("---")
    ansichts_modus = st.sidebar.radio(
        "👁️ Ansichts-Modus wechseln",
        ["Spieler-Ansicht", "🛡️ Spielleiter-Ansicht"],
        index=0,
        key="npc_view_mode"
    )
    ist_spielleiter = ansichts_modus == "🛡️ Spielleiter-Ansicht"

    # --- HILFSFUNKTION FÜR BILD-DATEINAMEN ---
    def generiere_sauberen_dateiname(npc_name):
        return "".join(c for c in npc_name if c.isalnum()).lower().strip() + ".png"

    def finde_lokales_npc_bild(npc_name):
        if not os.path.exists(BILDER_ORDNER):
            return None
        clean_npc = "".join(c for c in npc_name if c.isalnum()).lower().strip()
        for dateiname in os.listdir(BILDER_ORDNER):
            name_ohne_endung, ext = os.path.splitext(dateiname)
            if ext.lower() in [".png", ".jpg", ".jpeg"]:
                clean_datei = "".join(c for c in name_ohne_endung if c.isalnum()).lower()
                if clean_datei in clean_npc or clean_npc in clean_datei:
                    return os.path.join(BILDER_ORDNER, dateiname)
        return None

   # --- SCANNER & INITIALISIERUNG (NUR FÜR GM SICHTBAR) ---
    if ist_spielleiter:
        st.write("### 🛠️ Spielleiter-Werkzeuge (PDF-Verarbeitung)")
        
        # Lade die PDF-Texte (Hier wird jetzt nichts mehr abgeschnitten!)
        max_kapitel = fortschritt_stufen[fortschritt]
        aktive_texte = sammle_kampagnen_texte(max_kapitel)        
        kapitel_nur_texte = sammle_nur_kapitel_text(max_kapitel)  

        # Variablen vorab definieren, um den NameError zu verhindern
        btn_scan = False
        btn_init = False

        # Debug-Anzeige, damit du siehst, ob PDFs geladen wurden
        if not kapitel_nur_texte:
            st.warning("⚠️ Hinweis: Es wurden keine Textinhalte für das aktuelle Kapitel gefunden. Prüfe deinen PDF-Ordner!")

        # Zwei Buttons direkt nebeneinander anzeigen
        scan_col1, scan_col2 = st.columns(2)
        
        with scan_col1:
            btn_scan = st.button("🔍 Nach neuen NPCs scannen", key="btn_scan_kapitel", use_container_width=True)
        with scan_col2:
            btn_init = st.button("🚀 Dorf Willowshore initialisieren", key="btn_npc_init", use_container_width=True)

        # LOGIK FÜR DEN SCAN NACH NEUEN NPCs (KOMPLETTER TEXT)
        if btn_scan:
            if not api_key:
                st.error("API-Key fehlt!")
            elif not kapitel_nur_texte:
                st.error("Kein passendes Kapitel-PDF geladen!")
            else:
                client = genai.Client(api_key=api_key)
                vorhandene_namen = []
                for block in st.session_state.npc_inhalt.split("### "):
                    if block.strip() and not block.startswith("#"):
                        vorhandene_namen.append(block.split("\n")[0].strip())

                kapitel_text_gesamt = "\n".join(kapitel_nur_texte)
                
                scan_prompt = f"""Du bist ein extrem gründlicher Lektor für das Pathfinder-Abenteuer 'Season of the Ghosts'.
                Deine Aufgabe ist es, den GESAMTEN folgenden Text lückenlos nach neuen NPCs (wichtige Personen, Dorfbewohner, benannte Gegner) zu durchsuchen.
                Hier ist die Liste der NPCs, die wir BEREITS KENNEN: [{', '.join(vorhandene_namen)}]
                
                TEXT AUS DEN PDFs:
                {kapitel_text_gesamt}
                
                Antworte AUSSCHLIESSLICH mit den Namen der NEUEN NPCs, getrennt durch ein Komma. Wenn keine neuen gefunden werden, antworte mit: KEINE"""
                
                with st.spinner("Gemini sucht im kompletten Kapitel..."):
                    try:
                        response = client.models.generate_content(model='gemini-2.5-flash', contents=scan_prompt)
                        ergebnis = response.text.strip()
                        if ergebnis and ergebnis != "KEINE" and not ergebnis.startswith("#"):
                            gefundene_namen = [n.strip() for n in ergebnis.split(",") if n.strip()]
                            st.session_state.gescannter_npc_pool = sorted(list(set(gefundene_namen)))
                            st.success(f"🤖 Gemini hat {len(st.session_state.gescannter_npc_pool)} neue NPCs gefunden!")
                        else:
                            st.session_state.gescannter_npc_pool = []
                            st.info("Es wurden keine neuen NPCs gefunden.")
                    except Exception as e:
                        st.error(f"Fehler beim Scannen: {e}")

        # LOGIK FÜR DIE INITIALISIERUNG (Spielerleitfaden -> 100% ÖFFENTLICH, KEINE SPOILER)
        if btn_init:
            if not api_key:
                st.error("API-Key fehlt!")
            elif not aktive_texte:
                st.error("Keine Kampagnentexte vorhanden!")
            else:
                client = genai.Client(api_key=api_key)
                kapitel_text_gesamt = "\n".join(aktive_texte)
                
                init_prompt = f"""Du bist der Chronist für 'Season of the Ghosts'. Extrahiere JEDEN EINZELNEN benannten NPC aus dem beigefügten Spielerleitfaden.
                
⚠️ WICHTIGE REGEL: Dies ist der SPIELERLEITFADEN. Alle Informationen hierin sind für die Spieler von Anfang an bekannt und völlig spoilerfrei. 
Schreibe ALLE Details, Berufe, Beschreibungen und Hintergründe direkt in den öffentlichen Bereich. Die Sektion 'Spielleiter-Geheimnisse' bleibt komplett leer!

TEXT AUS DEM SPIELERLEITFADEN:
{kapitel_text_gesamt}

Nutze für jeden NPC exakt dieses Format:
### [Name des NPCs]
- **Gesinnung**: Verbündeter
#### 👥 Öffentlich bekannte Infos
- **Rolle im Dorf / Beruf**: [Beruf/Rolle hier eintragen]
- **Eigenschaften / Persönlichkeit**: [Beschreibung der Persönlichkeit und des Aussehens hier eintragen]
- **Bisherige Ereignisse**: Bekannt aus dem Spielerleitfaden.
- **Spieler-Notizen**: Keine zusätzlichen Notizen.
#### 🔒 Spielleiter-Geheimnisse

Antworte NUR mit dieser Markdown-Liste, beginnend mit '# BEKANNTE NPCs IN WILLOWSHORE'. Generiere so lange, bis du wirklich alle Personen erfasst hast!"""
                
                with st.spinner("Generiere vollständige NPC-Kartei aus dem Spielerleitfaden..."):
                    try:
                        response = client.models.generate_content(model='gemini-2.5-flash', contents=init_prompt)
                        st.session_state.npc_inhalt = response.text
                        with open(NPC_DATEI, "w", encoding="utf-8") as f:
                            f.write(response.text)
                        st.success("🎉 Spielerleitfaden erfolgreich eingelesen! Alle NPCs sind jetzt vollständig und öffentlich sichtbar.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Fehler bei der Einrichtung: {e}")

        # Wenn NPCs im Pool sind, Dropdown zum Importieren anzeigen
        if "gescannter_npc_pool" in st.session_state and st.session_state.gescannter_npc_pool:
            npc_auswahl = st.selectbox("Wähle einen erkannten NPC zum Importieren:", st.session_state.gescannter_npc_pool)
            
            if st.button("📥 Ausgewählten NPC importieren", key="btn_npc_import"):
                if not api_key:
                    st.error("API-Key fehlt!")
                else:
                    client = genai.Client(api_key=api_key)
                    kapitel_text_gesamt = "\n".join(kapitel_nur_texte)
                    
                    # Wir zwingen Gemini NUR die Gesinnung und die reinen Geheimnisse zu liefern!
                    detail_prompt = f"""Du bist der Chronist für eine Pen&Paper Kampagne. Analysiere den folgenden Text und extrahiere ALLE verfügbaren Informationen, Beschreibungen, Hintergründe, Werte und Story-Details zu dem NPC '{npc_auswahl}'.
                    
TEXTAUSZUG:
{kapitel_text_gesamt}

⚠️ DEINE REGELN:
1. Schätze zuerst die Gesinnung (Verbündeter, Gegner oder Unbekannt).
2. Schreibe ALLE Informationen über {npc_auswahl} als einzelne Stichpunkte auf, die jeweils mit "- **Geheimnis**:" beginnen.
3. Schreibe KEINE Überschriften, KEINE Einleitung und KEINE anderen Abschnitte. Nur die Gesinnung und die Geheimnis-Liste auf Deutsch!

Nutze EXAKT dieses Format für deine Antwort:
Gesinnung: [Verbündeter/Gegner/Unbekannt]
- **Geheimnis**: [Erste Info aus dem Text]
- **Geheimnis**: [Zweite Info aus dem Text]"""
                    
                    with st.spinner(f"Generiere geschützte Infos für {npc_auswahl}..."):
                        try:
                            response = client.models.generate_content(model='gemini-2.5-flash', contents=detail_prompt)
                            ki_antwort = response.text.strip()
                            
                            # Gesinnung aus der KI-Antwort parsen (Standard ist Unbekannt, falls die KI patzt)
                            gesinnung = "Unbekannt"
                            geheimnis_zeilen = []
                            
                            for zeile in ki_antwort.split("\n"):
                                if zeile.lower().startswith("gesinnung:"):
                                    wert = zeile.split(":", 1)[1].strip()
                                    if "verbündeter" in wert.lower(): gesinnung = "Verbündeter"
                                    elif "gegner" in wert.lower(): gesinnung = "Gegner"
                                elif zeile.strip().startswith("-"):
                                    # Sicherstellen, dass die Zeile das richtige Format hat
                                    if not "**Geheimnis**" in zeile:
                                        bereinigte_zeile = zeile.replace("-", "").strip()
                                        geheimnis_zeilen.append(f"- **Geheimnis**: {bereinigte_zeile}")
                                    else:
                                        geheimnis_zeilen.append(zeile.strip())
                            
                            # Falls die KI gar nichts geliefert hat, einen Standard-Punkt setzen
                            if not geheimnis_zeilen:
                                geheimnis_zeilen.append(f"- **Geheimnis**: Infos wurden aus dem Text extrahiert, müssen aber noch sortiert werden.")

                            geheimnisse_text = "\n".join(geheimnis_zeilen)

                            # HIER DER TRICK: Wir bauen das Markdown komplett in Python zusammen. 
                            # Der öffentliche Teil IST garantiert leer!
                            neuer_npc_text = f"""### {npc_auswahl}
- **Gesinnung**: {gesinnung}
#### 👥 Öffentlich bekannte Infos
- **Rolle im Dorf / Beruf**: Noch nicht im Spiel ermittelt.
- **Eigenschaften / Persönlichkeit**: Details unbekannt.
- **Bisherige Ereignisse**: Noch keine Begegnung im Spiel verzeichnet.
- **Spieler-Notizen**: Keine zusätzlichen Notizen.
#### 🔒 Spielleiter-Geheimnisse
{geheimnisse_text}"""

                            # In Datei speichern
                            neuer_gesamt_inhalt = st.session_state.npc_inhalt.strip() + "\n\n" + neuer_npc_text.strip()
                            with open(NPC_DATEI, "w", encoding="utf-8") as f:
                                f.write(neuer_gesamt_inhalt)
                                
                            st.session_state.npc_inhalt = neuer_gesamt_inhalt
                            st.session_state.gescannter_npc_pool.remove(npc_auswahl)
                            st.success(f"🎉 {npc_auswahl} wurde erfolgreich als 100% versteckter Spoiler-Eintrag importiert!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Fehler beim Import des NPCs: {e}")
        st.markdown("---")

    # --- PARSEN DER KATEGORIEN & BLÖCKE ---
    npc_bloecke = st.session_state.npc_inhalt.split("\n### ")
    kategorien = {"🟢 Verbündete": [], "🔴 Gegner": [], "⚪ Unbekannt": [], "🪦 Verstorbene": []}
    
    if npc_bloecke and npc_bloecke[0].startswith("### "):
        npc_bloecke[0] = npc_bloecke[0][4:]
    else:
        npc_bloecke = npc_bloecke[1:]

    for block in npc_bloecke:
        if block.strip():
            linien = block.split("\n")
            npc_name = linien[0].strip()
            
            if npc_name.startswith("#") or "Öffentlich bekannte Infos" in npc_name or "Spielleiter-Geheimnisse" in npc_name:
                continue
                
            ist_tot = False
            for linie in linien:
                if "**Status**" in linie and "Tot" in linie:
                    ist_tot = True
                    break
            
            gesinnung = "Unbekannt"
            for linie in linien:
                if "**Gesinnung**" in linie:
                    if "Verbündeter" in linie or "Verbündete" in linie:
                        gesinnung = "Verbündete"
                    elif "Gegner" in linie:
                        gesinnung = "Gegner"
                    break
            
            ziel_kat = "🪦 Verstorbene" if ist_tot else f"🟢 Verbündete" if gesinnung == "Verbündete" else f"🔴 Gegner" if gesinnung == "Gegner" else "⚪ Unbekannt"
            kategorien[ziel_kat].append((npc_name, block))

   # --- RE-USABLE NPC ANZEIGE-FUNKTION ---
    def zeige_npc_liste(npc_liste):
        if not npc_liste:
            st.info("Keine NPCs in dieser Kategorie.")
            return
            
        for npc_name, original_block in npc_liste:
            ist_tot = "- **Status**: Tot" in original_block or "💀" in npc_name
            anzeige_name = f"💀 {npc_name.replace('💀 ', '')}" if ist_tot else f"👤 {npc_name}"
            
            with st.expander(anzeige_name):
                col1, col2 = st.columns([1.5, 4])
                clean_name = npc_name.replace('💀 ', '')
                
                with col1:
                    bild_pfad = finde_lokales_npc_bild(clean_name)
                    if bild_pfad:
                        st.image(bild_pfad, use_container_width=True)
                    else:
                        st.markdown(f"<div style='text-align: center; font-size: 50px; background: #262730; border-radius: 10px; padding: 10px;'>{'💀' if ist_tot else '👤'}</div>", unsafe_allow_html=True)
                        st.caption("Kein Bild vorhanden")

                with col2:
                    block_text = original_block
                    oeffentlicher_teil = ""
                    geheimer_teil = ""
                    
                    if "#### 🔒 Spielleiter-Geheimnisse" in block_text:
                        teile = block_text.split("#### 🔒 Spielleiter-Geheimnisse")
                        oeffentlicher_teil = teile[0]
                        geheimer_teil = teile[1]
                    else:
                        oeffentlicher_teil = block_text
                    
                    st.markdown(oeffentlicher_teil)
                    
                    if ist_spielleiter and geheimer_teil.strip():
                        st.markdown("#### 🔒 Spielleiter-Geheimnisse (Nur für dich sichtbar)")
                        
                        geheimnis_linien = geheimer_teil.split("\n")
                        # HIER NEU: enumerate nutzen für einen absolut eindeutigen Key pro Zeile
                        for idx_linie, linie in enumerate(geheimnis_linien):
                            if linie.strip().startswith("-"):
                                g_col1, g_col2 = st.columns([4, 1])
                                with g_col1:
                                    st.markdown(linie)
                                with g_col2:
                                    # Eindeutiger Key durch Kombination aus Name, Text-Snippet und Zeilen-Index
                                    line_key = re.sub(r'\W+', '', linie)[:15]
                                    unique_btn_key = f"share_{clean_name}_{line_key}_{idx_linie}"
                                    
                                    if st.button("👁️ Teilen", key=unique_btn_key):
                                        alter_block_voll = "### " + original_block.strip()
                                        linien_original = original_block.split("\n")
                                        neue_linien = []
                                        
                                        idx_geheimnisse = -1
                                        for idx, l in enumerate(linien_original):
                                            if "#### 🔒 Spielleiter-Geheimnisse" in l:
                                                idx_geheimnisse = idx
                                                break
                                                
                                        if idx_geheimnisse != -1:
                                            gesuchte_linie = linie
                                            getroffen = False
                                            for idx, l in enumerate(linien_original):
                                                # Falls exakt diese Zeile gemeint ist (beim ersten Match löschen)
                                                if l.strip() == gesuchte_linie.strip() and not getroffen:
                                                    getroffen = True
                                                    continue
                                                if idx == idx_geheimnisse:
                                                    neue_linien.append(gesuchte_linie)
                                                neue_linien.append(l)
                                                
                                            neuer_block_voll = "### " + "\n".join(neue_linien).strip()
                                            neuer_gesamt_inhalt = st.session_state.npc_inhalt.replace(alter_block_voll, neuer_block_voll)
                                            
                                            with open(NPC_DATEI, "w", encoding="utf-8") as f:
                                                f.write(neuer_gesamt_inhalt)
                                            st.session_state.npc_inhalt = neuer_gesamt_inhalt
                                            st.success("Info erfolgreich für Spieler freigeschaltet!")
                                            st.rerun()
                            else:
                                if linie.strip():
                                    st.markdown(linie)
                                    
                    st.write("---")
                    
                    if ist_spielleiter:
                        b_col1, b_col2 = st.columns(2)
                        with b_col1:
                            st.caption("Beziehung anpassen:")
                            if not ist_tot:
                                z_col1, z_col2, z_col3 = st.columns(3)
                                def ändere_gesinnung(ziel_gesinnung):
                                    alter_block = "### " + original_block.strip()
                                    linien = original_block.split("\n")
                                    for idx, linie in enumerate(linien):
                                        if "**Gesinnung**" in linie:
                                            linien[idx] = f"- **Gesinnung**: {ziel_gesinnung}"
                                    neuer_block = "### " + "\n".join(linien).strip()
                                    neuer_gesamt_inhalt = st.session_state.npc_inhalt.replace(alter_block, neuer_block)
                                    with open(NPC_DATEI, "w", encoding="utf-8") as f:
                                        f.write(neuer_gesamt_inhalt)
                                    st.session_state.npc_inhalt = neuer_gesamt_inhalt
                                    st.rerun()
                                with z_col1:
                                    if st.button("🟢", key=f"btn_verb_{npc_name}"): ändere_gesinnung("Verbündeter")
                                with z_col2:
                                    if st.button("🔴", key=f"btn_gegn_{npc_name}"): ändere_gesinnung("Gegner")
                                with z_col3:
                                    if st.button("⚪", key=f"btn_unb_{npc_name}"): ändere_gesinnung("Unbekannt")
                        
                        with b_col2:
                            st.caption("Lebensstatus:")
                            def setze_lebensstatus(tot_machen=True):
                                alter_block = "### " + original_block.strip()
                                linien = original_block.split("\n")
                                hat_status_feld = False
                                for idx, linie in enumerate(linien):
                                    if "**Status**" in linie:
                                        linien[idx] = "- **Status**: Tot" if tot_machen else "- **Status**: Lebendig"
                                        hat_status_feld = True
                                if not hat_status_feld:
                                    linien.insert(2, "- **Status**: Tot" if tot_machen else "- **Status**: Lebendig")
                                neuer_block = "### " + "\n".join(linien).strip()
                                neuer_gesamt_inhalt = st.session_state.npc_inhalt.replace(alter_block, neuer_block)
                                with open(NPC_DATEI, "w", encoding="utf-8") as f: f.write(neuer_gesamt_inhalt)
                                st.session_state.npc_inhalt = neuer_gesamt_inhalt
                                st.rerun()
                            if not ist_tot:
                                kill_check = st.checkbox("☠️ Tod bestätigen", key=f"chk_kill_{npc_name}")
                                if st.button("❌ Eliminieren", key=f"btn_kill_{npc_name}", disabled=not kill_check, type="primary"):
                                    setze_lebensstatus(tot_machen=True)
                            else:
                                if st.button("✨ Wiederbeleben", key=f"btn_revive_{npc_name}"): setze_lebensstatus(tot_machen=False)

                        st.write("---")
                        with st.expander("📝 Steckbrief manuell bearbeiten"):
                            voller_block_text = f"### {original_block.strip()}"
                            neuer_block_text = st.text_area("Inhalt bearbeiten:", value=voller_block_text, height=250, key=f"edit_area_{npc_name}")
                            edit_col1, edit_col2 = st.columns(2)
                            with edit_col1:
                                if st.button("💾 Speichern", key=f"btn_save_edit_{npc_name}", use_container_width=True):
                                    neuer_gesamt_inhalt = st.session_state.npc_inhalt.replace(voller_block_text, neuer_block_text.strip())
                                    with open(NPC_DATEI, "w", encoding="utf-8") as f: f.write(neuer_gesamt_inhalt)
                                    st.session_state.npc_inhalt = neuer_gesamt_inhalt
                                    st.rerun()
                            with edit_col2:
                                loesch_bestaetigung = st.checkbox("🗑️ Löschen?", key=f"chk_del_{npc_name}")
                                if st.button("🗑️ NPC komplett löschen", key=f"btn_del_{npc_name}", disabled=not loesch_bestaetigung, type="primary", use_container_width=True):
                                    neuer_gesamt_inhalt = st.session_state.npc_inhalt.replace(voller_block_text, "").replace("\n\n\n", "\n\n")
                                    with open(NPC_DATEI, "w", encoding="utf-8") as f: f.write(neuer_gesamt_inhalt)
                                    st.session_state.npc_inhalt = neuer_gesamt_inhalt
                                    st.rerun()

    st.write("### Aktuelle NPC-Kartei:")
    suchbegriff = st.text_input("🔍 NPC nach Namen suchen:", value="", placeholder="Name...").strip().lower()

    def filtere_liste(npc_liste, begriff):
        if not begriff: return npc_liste
        return [npc for npc in npc_liste if begriff in npc[0].lower()]

    sub_tab1, sub_tab2, sub_tab3, sub_tab4 = st.tabs(["🟢 Verbündete", "🔴 Gegner", "⚪ Unbekannt", "🪦 Verstorbene"])
    with sub_tab1: zeige_npc_liste(filtere_liste(kategorien["🟢 Verbündete"], suchbegriff))
    with sub_tab2: zeige_npc_liste(filtere_liste(kategorien["🔴 Gegner"], suchbegriff))
    with sub_tab3: zeige_npc_liste(filtere_liste(kategorien["⚪ Unbekannt"], suchbegriff))
    with sub_tab4: zeige_npc_liste(filtere_liste(kategorien["🪦 Verstorbene"], suchbegriff))
    
    if ist_spielleiter:
        st.write("---")
        st.write("### 📝 Neue Erlebnisse für bestehende NPCs eintragen")
        notizen_npc = st.text_area("Was ist passiert?", key="npc_notizen_eingabe_feld")

        if st.button("NPC-Chronik aktualisieren", key="btn_npc"):
            if not api_key or not notizen_npc: st.error("Eingabe fehlt!")
            else:
                client = genai.Client(api_key=api_key)
                npc_update_prompt = f"""Du bist der Chronist. Aktualisiere die NPC-Chronik basierend auf den neuen Notizen:\n{notizen_npc}\n\n
                ⚠️ WICHTIG: Ändere NIEMALS die Trennlinien '#### 👥 Öffentlich bekannte Infos' und '#### 🔒 Spielleiter-Geheimnisse'. Lösche keine Einträge davor oder danach, hänge neue Infos logisch an."""
                with st.spinner("Gemini aktualisiert..."):
                    try:
                        response = client.models.generate_content(model='gemini-2.5-flash', contents=npc_update_prompt)
                        st.session_state.npc_inhalt = response.text
                        with open(NPC_DATEI, "w", encoding="utf-8") as f: f.write(response.text)
                        st.success("🎉 Aktualisiert!")
                        st.rerun()
                    except Exception as e: st.error(f"Fehler: {e}")