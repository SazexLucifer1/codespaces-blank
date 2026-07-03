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

    st.write("### 📥 Kapitel-PDFs nach neuen NPCs scannen")
    
    max_kapitel = fortschritt_stufen[fortschritt]
    aktive_texte = sammle_kampagnen_texte(max_kapitel)        
    kapitel_nur_texte = sammle_nur_kapitel_text(max_kapitel)  

    if st.button("🔍 PDFs nach NPCs durchsuchen", key="btn_scan_kapitel"):
        if not api_key:
            st.error("API-Key fehlt!")
        elif not kapitel_nur_texte:
            st.error("Kein passendes Kapitel-PDF im Ordner gefunden!")
        else:
            client = genai.Client(api_key=api_key)
            
            vorhandene_namen = []
            for block in st.session_state.npc_inhalt.split("### "):
                if block.strip() and not block.startswith("#"):
                    vorhandene_namen.append(block.split("\n")[0].strip())

            scan_prompt = f"""Du bist ein extrem gründlicher Lektor für das Pathfinder-Abenteuer 'Season of the Ghosts'.
            Deine Aufgabe ist es, den bereitgestellten Text Zeile für Zeile nach ALLEN namentlich erwähnten Personen (NPCs) zu durchsuchen.
            
            Berücksichtige JEDEN Charakter – egal ob es sich um wichtige Dorfbewohner, Händler, Wachen, Geister, Feinde mit Namen oder historische Figuren handelt, die im Kapitel auftauchen!
            
            Hier ist die Liste der NPCs, die wir BEREITS KENNEN: [{', '.join(vorhandene_namen)}]
            
            Aufgabe:
            1. Scanne den gesamten Text nach JEDEM englischen Eigennamen, der eine Person beschreibt.
            2. Vergleiche sie mit der obigen Liste.
            3. Ignoriere Namen, die bereits bekannt sind.
            4. Erstelle eine kommagetrennte Liste NUR mit den neuen, bisher unentdeckten Namen.
            
            ⚠️ WICHTIGE ANWEISUNG FÜR DIE AUSGABE:
            Antworte AUSSCHLIESSLICH mit den Namen der NPCs, getrennt durch ein Komma (z.B. Mathew, Maku, Hai-er Ha). 
            Schreibe KEINE Einleitung, KEINE Aufzählungszeichen, KEIN "Hier sind die NPCs" und KEINE Erklärungen! 
            Wenn du absolut keine neuen Personen findest, antworte mit dem einzelnen WORD: KEINE"""
            with st.spinner("Gemini liest die PDFs und sucht nach Charakteren..."):
                try:
                    response = client.models.generate_content(model='gemini-2.5-flash', contents=kapitel_nur_texte + [scan_prompt])
                    ergebnis = response.text.strip()
                    
                    if ergebnis and ergebnis != "KEINE":
                        gefundene_namen = [n.strip() for n in ergebnis.split(",") if n.strip()]
                        st.session_state.gescannter_npc_pool = sorted(list(set(gefundene_namen)))
                        st.success(f"🤖 Gemini hat {len(st.session_state.gescannter_npc_pool)} neue NPCs gefunden!")
                    else:
                        st.session_state.gescannter_npc_pool = []
                        st.info("Es wurden keine neuen NPCs in den PDFs gefunden.")
                except Exception as e:
                    st.error(f"Fehler beim Scannen: {e}")

    if "gescannter_npc_pool" in st.session_state and st.session_state.gescannter_npc_pool:
        npc_auswahl = st.selectbox("Wähle einen erkannten NPC zum Importieren:", st.session_state.gescannter_npc_pool)
        
        if st.button("📥 Ausgewählten NPC importieren", key="btn_npc_import"):
            if not api_key:
                st.error("API-Key fehlt!")
            else:
                client = genai.Client(api_key=api_key)
                kapitel_text_gesamt = "\n".join(kapitel_nur_texte)
                
                detail_prompt = f"""Du bist der Chronist. Erstelle für den NPC '{npc_auswahl}' einen absolut SPOILERFREIEN Steckbrief auf DEUTSCH basierend auf diesem Text:
                {kapitel_text_gesamt[:50000]}

                Nutze exakt dieses Format:
                ### {npc_auswahl}
                - **Gesinnung**: (Schätze basierend auf dem Text: Verbündeter, Gegner oder Unbekannt)
                - **Rolle im Dorf / Beruf**: ...
                - **Eigenschaften / Persönlichkeit**: ...
                - **Bisherige Ereignisse**: Noch keine Begegnung im Spiel verzeichnet.
                - **Spieler-Notizen**: Keine zusätzlichen Notizen.

                ⚠️ STRIKTE ANTI-SPOILER-REGELN:
                1. Du darfst NUR Informationen verwenden, die JEDER Dorfbewohner oder ein reisender Held beim ALLERERSTEN, oberflächlichen Kennenlernen sofort sieht oder weiß (z.B. "Er ist der örtliche Schmied", "Sie wirkt stets mürrisch").
                2. IGNORIERE komplett alle Abschnitte, die mit "Background", "Secret", "Developments", "Stats" oder "Quest" zu tun haben!
                3. Wenn im Text steht, dass der NPC ein Geheimnis hat, Schulden hat, ein Monster ist, jemanden hintergeht oder eine geheime Motivation besitzt: SCHREIBE ES NICHT AUF! Lass es weg.
                4. Eigennamen/Traits im Englischen lassen. Antworte NUR mit den 5 Stichpunkten für diesen einen NPC!"""
                
                with st.spinner(f"Generiere spoilerfreien Steckbrief & passendes Artwork für {npc_auswahl}..."):
                    try:
                        # 1. Text generieren
                        response = client.models.generate_content(model='gemini-2.5-flash', contents=[detail_prompt])
                        neuer_npc_text = response.text
                        
                        neuer_gesamt_inhalt = st.session_state.npc_inhalt.strip() + "\n\n" + neuer_npc_text.strip()
                        with open(NPC_DATEI, "w", encoding="utf-8") as f:
                            f.write(neuer_gesamt_inhalt)
                            
                        st.session_state.npc_inhalt = neuer_gesamt_inhalt
                        st.session_state.gescannter_npc_pool.remove(npc_auswahl)
                        
                        st.success(f"🎉 {npc_auswahl} wurde zur Chronik hinzugefügt!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Fehler beim Import: {e}")

    st.markdown("---")

    if len(st.session_state.npc_inhalt.strip().split("\n")) <= 4:
        st.info("💡 Die NPC-Chronik ist noch leer. Du kannst Gemini bitten, alle bekannten Dorfbewohner direkt aus dem Spieler-Leitfaden einzulesen!")
        if st.button("🔍 Dorf Willowshore automatisch scannen (Ersteinrichtung)", key="btn_npc_init"):
            if not api_key:
                st.error("API-Key fehlt!")
            else:
                client = genai.Client(api_key=api_key)
                init_prompt = """Du bist der Chronist für 'Season of the Ghosts'. Deine Aufgabe ist es, die Ersteinrichtung der NPC-Kartei vorzunehmen.
                    
Durchsuche die bereitgestellten Kampagnen-Texte nach JEDEM namentlich erwähnten NPC, den die Spieler zu Beginn der Kampagne in Willowshore kennen.

Erstelle für jeden dieser NPCs einen Eintrag im folgenden Format:
### [Name des NPCs]
- **Gesinnung**: (Schätze basierend auf dem Text: Verbündeter, Gegner oder Unbekannt)
- **Rolle im Dorf / Beruf**: (Was tut die Person in Willowshore?)
- **Eigenschaften / Persönlichkeit**: (Merkmale, Traits aus dem Buch)
- **Bisherige Ereignisse**: Noch keine Begegnung im Spiel verzeichnet.
- **Spieler-Notizen**: Keine zusätzlichen Notizen.

⚠️ STRIKTE REGELN:
1. SPRACHE: Schreibe alle Beschreibungen und Fließtexte auf DEUTSCH.
2. EIGENNAMEN & TRAITS: Übersetze NIEMALS englische Eigennamen, Ortsnamen (z.B. Willowshore) oder feststehende Spieleditor-Begriffe/Traits (wie ugly-cute). Lass diese im englischen Original!
3. Keine Spoiler aus den Kapitel-PDFs!
4. Antworte NUR mit der Markdown-Liste, beginnend mit der Überschrift '# BEKANNTE NPCs IN WILLOWSHORE'."""

                with st.spinner("Gemini scannt die PDFs nach allen Dorfbewohnern..."):
                    try:
                        response = client.models.generate_content(model='gemini-2.5-flash', contents=aktive_texte + [init_prompt])
                        st.session_state.npc_inhalt = response.text
                        with open(NPC_DATEI, "w", encoding="utf-8") as f:
                            f.write(response.text)
                        st.success("🎉 Dorf erfolgreich gescannt! Alle NPCs wurden geladen. (Hinweis: Du kannst Bilder für sie in den Detail-Ausklappmenüs würfeln!)")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Fehler beim Scannen: {e}")

    npc_bloecke = st.session_state.npc_inhalt.split("### ")
    
    kategorien = {
        "🟢 Verbündete": [],
        "🔴 Gegner": [],
        "⚪ Unbekannt": [],
        "🪦 Verstorbene": []
    }
    
    for block in npc_bloecke[1:]:
        if block.strip():
            linien = block.split("\n")
            npc_name = linien[0].strip()
            restlicher_text = "\n".join(linien[1:])
            
            ist_tot = False
            for linie in linien:
                if "**Status**" in linie and "Tot" in linie:
                    ist_tot = True
                    break
            
            if ist_tot:
                kategorien["🪦 Verstorbene"].append((npc_name, restlicher_text, block))
            else:
                gesinnung = "Unbekannt"
                for linie in linien:
                    if "**Gesinnung**" in linie:
                        if "Verbündeter" in linie or "Verbündete" in linie:
                            gesinnung = "Verbündete"
                        elif "Gegner" in linie:
                            gesinnung = "Gegner"
                
                if gesinnung == "Verbündete":
                    kategorien["🟢 Verbündete"].append((npc_name, restlicher_text, block))
                elif gesinnung == "Gegner":
                    kategorien["🔴 Gegner"].append((npc_name, restlicher_text, block))
                else:
                    kategorien["⚪ Unbekannt"].append((npc_name, restlicher_text, block))

    def zeige_npc_liste(npc_liste):
        if not npc_liste:
            st.info("Keine NPCs in dieser Kategorie.")
            return
            
        for npc_name, restlicher_text, original_block in npc_liste:
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
                    st.markdown(restlicher_text)
                    st.write("---")
                    
                    b_col1, b_col2 = st.columns(2)
                    
                    with b_col1:
                        st.caption("Beziehung anpassen:")
                        if not ist_tot:
                            z_col1, z_col2, z_col3 = st.columns(3)
                            
                            def ändere_gesinnung(ziel_gesinnung):
                                alter_block = "### " + original_block.strip()
                                linien = original_block.split("\n")
                                hat_gesinnung_feld = False
                                for idx, linie in enumerate(linien):
                                    if "**Gesinnung**" in linie:
                                        linien[idx] = f"- **Gesinnung**: {ziel_gesinnung}"
                                        hat_gesinnung_feld = True
                                if not hat_gesinnung_feld:
                                    linien.insert(1, f"- **Gesinnung**: {ziel_gesinnung}")
                                neuer_block = "### " + "\n".join(linien).strip()
                                neuer_gesamt_inhalt = st.session_state.npc_inhalt.replace(alter_block, neuer_block)
                                with open(NPC_DATEI, "w", encoding="utf-8") as f:
                                    f.write(neuer_gesamt_inhalt)
                                st.session_state.npc_inhalt = neuer_gesamt_inhalt
                                st.success(f"Gesinnung von {npc_name} geändert!")
                                st.rerun()

                            with z_col1:
                                if st.button("🟢 Verbündeter", key=f"btn_verb_{npc_name}"):
                                    ändere_gesinnung("Verbündeter")
                            with z_col2:
                                if st.button("🔴 Gegner", key=f"btn_gegn_{npc_name}"):
                                    ändere_gesinnung("Gegner")
                            with z_col3:
                                if st.button("⚪ Unbekannt", key=f"btn_unb_{npc_name}"):
                                    ändere_gesinnung("Unbekannt")
                        else:
                            st.warning("Dieser NPC ist verstorben. Gesinnung kann nicht geändert werden.")
                    
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
                                    break
                            if not hat_status_feld:
                                linien.insert(2, "- **Status**: Tot" if tot_machen else "- **Status**: Lebendig")
                                
                            neuer_block = "### " + "\n".join(linien).strip()
                            neuer_gesamt_inhalt = st.session_state.npc_inhalt.replace(alter_block, neuer_block)
                            
                            with open(NPC_DATEI, "w", encoding="utf-8") as f:
                                f.write(neuer_gesamt_inhalt)
                            st.session_state.npc_inhalt = neuer_gesamt_inhalt
                            st.rerun()

                        if not ist_tot:
                            kill_check = st.checkbox("☠️ Ich bestätige, dass dieser NPC stirbt", key=f"chk_kill_{npc_name}")
                            if st.button("❌ NPC eliminieren", key=f"btn_kill_{npc_name}", disabled=not kill_check, type="primary"):
                                setze_lebensstatus(tot_machen=True)
                        else:
                            if st.button("✨ NPC wiederbeleben", key=f"btn_revive_{npc_name}"):
                                setze_lebensstatus(tot_machen=False)

                    # --- NEUE MANUELLE BEARBEITUNGS-FUNKTION ---
                    st.write("---")
                    with st.expander("📝 Steckbrief manuell bearbeiten"):
                        voller_block_text = f"### {original_block.strip()}"
                        neuer_block_text = st.text_area(
                            f"Inhalt bearbeiten für {npc_name}:",
                            value=voller_block_text,
                            height=250,
                            key=f"edit_area_{npc_name}"
                        )
                        if st.button("💾 Änderungen speichern", key=f"btn_save_edit_{npc_name}", use_container_width=True):
                            if neuer_block_text.strip():
                                alter_block = f"### {original_block.strip()}"
                                neuer_gesamt_inhalt = st.session_state.npc_inhalt.replace(alter_block, neuer_block_text.strip())
                                with open(NPC_DATEI, "w", encoding="utf-8") as f:
                                    f.write(neuer_gesamt_inhalt)
                                st.session_state.npc_inhalt = neuer_gesamt_inhalt
                                st.success("Änderung erfolgreich gespeichert!")
                                st.rerun()
                            else:
                                st.error("Der Text darf nicht leer sein.")

    st.write("### Aktuelle NPC-Kartei:")
    
    suchbegriff = st.text_input(
        "🔍 NPC nach Namen suchen (Enter zum Bestätigen):", 
        value="", 
        placeholder="Name eingeben und Enter drücken..."
    ).strip().lower()

    def filtere_liste(npc_liste, begriff):
        if not begriff:
            return npc_liste
        return [npc for npc in npc_liste if begriff in npc[0].lower()]

    sub_tab1, sub_tab2, sub_tab3, sub_tab4 = st.tabs(["🟢 Verbündete", "🔴 Gegner", "⚪ Unbekannt", "🪦 Verstorbene"])
    
    with sub_tab1:
        zeige_npc_liste(filtere_liste(kategorien["🟢 Verbündete"], suchbegriff))
    with sub_tab2:
        zeige_npc_liste(filtere_liste(kategorien["🔴 Gegner"], suchbegriff))
    with sub_tab3:
        zeige_npc_liste(filtere_liste(kategorien["⚪ Unbekannt"], suchbegriff))
    with sub_tab4:
        zeige_npc_liste(filtere_liste(kategorien["🪦 Verstorbene"], suchbegriff))
    
    st.write("---")
    st.write("### 📝 Neue Erlebnisse für bestehende NPCs eintragen")
    notizen_npc = st.text_area(
        "Was ist mit den NPCs passiert? (z.B. Mathew hat uns geholfen, Maku ist wütend):", 
        key="npc_notizen_eingabe_feld",
        placeholder="Schreibe hier die Ereignisse der Session rein..."
    )

    if st.button("NPC-Chronik aktualisieren", key="btn_npc"):
        if not api_key:
            st.error("API-Key fehlt!")
        elif not notizen_npc:
            st.warning("Bitte gib Notizen ein!")
        else:
            client = genai.Client(api_key=api_key)

            import difflib
            vorhandene_namen = []
            for block in st.session_state.npc_inhalt.split("### "):
                if block.strip() and not block.startswith("#"):
                    vorhandene_namen.append(block.split("\n")[0].strip())
            
            erkannte_ordnung = []
            notiz_clean = notizen_npc.lower()
            
            for name in vorhandene_namen:
                name_clean = "".join(c for c in name if c.isalnum() or c == " ").lower().replace("„", "").replace("“", "")
                name_teile = name_clean.split()
                for teil in name_teile:
                    if len(teil) > 2:
                        for wort in notiz_clean.split():
                            äquivalent = difflib.get_close_matches(wort, [teil], n=1, cutoff=0.55)
                            if äquivalent and name not in erkannte_ordnung:
                                erkannte_ordnung.append(name)
                                
            for wort in re.findall(r'\b\w+\b', notizen_npc):
                if len(wort) > 3:
                    treffer = difflib.get_close_matches(wort, vorhandene_namen, n=1, cutoff=0.55)
                    if treffer and treffer[0] not in erkannte_ordnung:
                        erkannte_ordnung.append(treffer[0])
            
            hinweis_erkannte_namen = ""
            if erkannte_ordnung:
                hinweis_erkannte_namen = "\n💡 HINWEIS FÜR DICH:\n"
                for name in erkannte_ordnung:
                    hinweis_erkannte_namen += f"- In den Notizen wurden Details zu {name} gefunden.\n"

            npc_update_prompt = f"""Du bist der Chronist. Aktualisiere die NPC-Chronik basierend auf den neuen Notizen.
            
Hier sind die neuen Notizen:
{notizen_npc}

{hinweis_erkannte_namen}

Bitte passe die Einträge der betroffenen NPCs in der Chronik an, ohne wichtige alte Informationen zu löschen. Antworte mit der vollständig aktualisierten Chronik im bekannten Format."""

            with st.spinner("Gemini aktualisiert die NPC-Chronik..."):
                try:
                    response = client.models.generate_content(
                        model='gemini-2.5-flash', 
                        contents=[st.session_state.npc_inhalt, npc_update_prompt]
                    )
                    st.session_state.npc_inhalt = response.text
                    with open(NPC_DATEI, "w", encoding="utf-8") as f:
                        f.write(response.text)
                    st.success("🎉 NPC-Chronik erfolgreich aktualisiert!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Fehler beim Aktualisieren: {e}")