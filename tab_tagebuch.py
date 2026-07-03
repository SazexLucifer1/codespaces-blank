import streamlit as st
import os
import datetime
import re
from google import genai

def render_tab(api_key, fortschritt_stufen, fortschritt, lokale_charaktere, sammle_kampagnen_texte, sammle_charakter_texte):
    st.subheader("📖 Interaktives Kampagnen-Tagebuch")

    # Ordner für die einzelnen Tagebucheinträge definieren und erstellen
    TAGEBUCH_ORDNER = "tagebuch_eintraege"
    if not os.path.exists(TAGEBUCH_ORDNER):
        os.makedirs(TAGEBUCH_ORDNER)

    # --- NEUEN EINTRAG ERSTELLEN ---
    st.write("### ✍️ Neuen Tagebucheintrag von KI verfassen lassen")
    
    # FILTER: Nur echte Namen zulassen, keine verstreuten Einzelbuchstaben von "Zarion"
    valide_charaktere = []
    if lokale_charaktere:
        if isinstance(lokale_charaktere, str):
            valide_charaktere = [lokale_charaktere]
        else:
            valide_charaktere = [c for c in lokale_charaktere if len(str(c)) > 1]

    if valide_charaktere:
        charakter_auswahl = st.selectbox("Wer schreibt diesen Eintrag? (Persönlichkeit & Stil passen sich an):", valide_charaktere, key="tb_char_select")
    else:
        st.info("Füge PDFs in 'spieler_Charaktere' ein, um einen Helden zu wählen.")
        charakter_auswahl = "Unbekannter Held"

    titel_eingabe = st.text_input(
        "Titel für diesen Spielabend / Eintrag:", 
        placeholder="z.B. Sitzung 5: Der Geist im Teehaus",
        key="tb_titel_neu"
    )
    
    text_eingabe = st.text_area(
        "Was ist heute passiert? (Deine Notizen, Rohdaten oder Stichpunkte):", 
        placeholder="z.B. Wir haben Maku getroffen. Valeros war betrunken. Haben Tempel untersucht...",
        key="tb_text_neu"
    )

    if st.button("🪄 Eintrag von Charakter schreiben lassen & speichern", use_container_width=True, key="btn_save_diary"):
        if not titel_eingabe.strip() or not text_eingabe.strip():
            st.error("Bitte gib sowohl einen Titel als auch Stichpunkte ein!")
        elif not api_key:
            st.error("API-Key fehlt! Ohne Schlüssel kann die KI nicht im Stil des Helden schreiben.")
        else:
            # 1. Charakter-Text (PDF) sammeln
            charakter_pdf_text = sammle_charakter_texte(charakter_auswahl) if charakter_auswahl != "Unbekannter Held" else ""
            
            # 2. Reine Zahl aus dem Fortschritt holen für die PDF-Funktion
            if isinstance(fortschritt, str):
                zahlen_finder = re.findall(r'\d+', fortschritt)
                kapitel_zahl = int(zahlen_finder[0]) if zahlen_finder else 1
            else:
                kapitel_zahl = int(fortschritt)
            
            kapitel_pdf_text = sammle_kampagnen_texte(kapitel_zahl)
            
            # 3. KI-Prompt aufbauen (JETZT MIT STRIKTER SPOILER-SPERRE)
            diary_prompt = f"""Du bist der Pathfinder 2e Charakter '{charakter_auswahl}'. 
Schreibe einen Tagebucheintrag aus deiner persönlichen Sicht.

### DEIN CHARAKTERBLATT / HINTERGRUND:
{charakter_pdf_text if charakter_pdf_text else 'Nutze den Namen und deine Fantasie für eine passende Persönlichkeit.'}

### OFFIZIELLER KAMPAGNEN-HINTERGRUND (NUR FÜR NAMENSABGLEICH):
{kapitel_pdf_text if kapitel_pdf_text else 'Kein Kapitel-Text verfügbar.'}

### DIE STICHPAKTE DES ABENDS (DAS HABEN DIE SPIELER ERLEBT):
"{text_eingabe.strip()}"

### 🚨 STRIKTE ANWEISUNGEN GEGEN SPOILER (SEHR WICHTIG):
1. Die "Stichpunkte des Abends" sind das EINZIGE, was in der Spielsitzung tatsächlich passiert ist.
2. Nutze den "Kampagnen-Hintergrund" AUSSCHLIESSLICH, um die Schreibweise von Orten oder NPCs zu korrigieren, die BEREITS IN DEN STICHPUNKTEN ERWÄHNT WURDEN.
3. ⚠️ ABSOLUTES SPOILER-VERBOT: Erwähne KEINE Plottwists, geheimen Absichten von NPCs, wahren Identitäten von Monstern oder zukünftigen Ereignisse aus dem Kampagnen-Hintergrund, die NICHT in den Stichpunkten stehen! Wenn die Spieler dachten, NPC X sei nett, darf im Tagebuch nicht stehen, dass er ein Verräter ist, selbst wenn es im Buch steht!
4. Schreibe kurz und knackig (max. 150-200 Wörter), auf DEUTSCH und komplett "in-character".
Antworte NUR mit dem fertigen Tagebuchtext, ohne Metakommentare!"""

            with st.spinner(f"✍️ {charakter_auswahl} filtert Spoiler und schreibt das Tagebuch..."):
                try:
                    client = genai.Client(api_key=api_key)
                    response = client.models.generate_content(
                        model='gemini-2.5-flash', 
                        contents=[diary_prompt]
                    )
                    ki_tagebuch_text = response.text.strip()
                    
                    jetzt = datetime.datetime.now()
                    zeit_string = jetzt.strftime("%Y_%m_%d_%H%M%S")
                    anzeige_datum = jetzt.strftime("%d.%m.%Y um %H:%M Uhr")
                    
                    clean_char_name = "".join(c for c in charakter_auswahl if c.isalnum() or c in ("_", "-"))
                    dateiname = f"eintrag_{zeit_string}_{clean_char_name}.txt"
                    dateipfad = os.path.join(TAGEBUCH_ORDNER, dateiname)
                    
                    metadaten = f"📅 {anzeige_datum} | ✍️ Im Stil von: {charakter_auswahl} (Kapitel {kapitel_zahl})"
                    inhalt = f"{titel_eingabe.strip()}\n{metadaten}\n{ki_tagebuch_text}"
                    
                    with open(dateipfad, "w", encoding="utf-8") as f:
                        f.write(inhalt)
                        
                    st.success(f"🎉 Der spoilerfreie Eintrag wurde für Kapitel {kapitel_zahl} generiert!")
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Fehler bei der KI-Generierung: {e}")

    st.markdown("---")

    # --- TAGEBUCH-ARCHIV ANZEIGEN & SORTIEREN ---
    st.write("### 🗄️ Vergangene Tagebucheinträge")

    if not os.path.exists(TAGEBUCH_ORDNER):
        alle_dateien = []
    else:
        alle_dateien = [f for f in os.listdir(TAGEBUCH_ORDNER) if f.endswith(".txt")]
    
    if not alle_dateien:
        st.info("Es wurden noch keine Tagebucheinträge für diese Kampagne angelegt.")
    else:
        sortierung = st.radio(
            "Sortierung der Chronik:", 
            options=["📅 Neueste Einträge oben", "⏳ Älteste Einträge oben"],
            horizontal=True,
            key="rb_diary_sort"
        )
        
        if "Neueste Einträge oben" in sortierung:
            sortierte_dateien = sorted(alle_dateien, reverse=True)
        else:
            sortierte_dateien = sorted(alle_dateien)

        # --- DAS POPUP-FENSTER (DIALOG) ---
        @st.dialog("📖 Tagebucheintrag Details")
        def zeige_eintrag_popup(pfad_zur_datei, datei_name):
            with open(pfad_zur_datei, "r", encoding="utf-8") as f:
                zeilen = f.readlines()
            
            if len(zeilen) >= 2:
                titel = zeilen[0].strip()
                meta_info = zeilen[1].strip()
                rest_text = "".join(zeilen[2:])
                
                st.subheader(titel)
                st.caption(meta_info)
                st.markdown("---")
                st.write(rest_text)
            else:
                st.error("Datei beschädigt oder im falschen Format.")
            
            st.markdown("---")
            if st.button("🗑️ Diesen Eintrag löschen", type="secondary", use_container_width=True):
                os.remove(pfad_zur_datei)
                st.rerun()

        # --- BUTTON-LISTE GENERIEREN ---
        for datei in sortierte_dateien:
            pfad = os.path.join(TAGEBUCH_ORDNER, datei)
            
            with open(pfad, "r", encoding="utf-8") as f:
                erste_zeile = f.readline().strip()
                zweite_zeile = f.readline().strip()
            
            button_label = f"📝 {zweite_zeile} — »{erste_zeile}«"
            
            if st.button(button_label, key=f"btn_diag_{datei}", use_container_width=True):
                zeige_eintrag_popup(pfad, datei)