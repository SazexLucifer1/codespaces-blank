import streamlit as st
import os
import re
import time
from google import genai
from pypdf import PdfReader
from dotenv import load_dotenv

# Importiere das Shop-Modul
from shinzo_shop import render_shop_tab

# Importiere die einzelnen Tabs
import tab_tagebuch
import tab_quests
import tab_npcs

# Lädt die Variablen aus der .env-Datei aktiv in das System
load_dotenv()

st.set_page_config(page_title="Season of the Ghosts Assistent", layout="wide")
st.title("⛩️ Season of the Ghosts: Kampagnen- & Charakter-Assistent")
st.write("Free-Tier Version: PDFs werden lokal als Text ausgelesen (kein unnötiger Bild-Upload).")

env_key = os.getenv("GEMINI_API_KEY")
raw_key = st.sidebar.text_input("Dein Gemini API-Key:", value=env_key if env_key else "", type="password")

if raw_key:
    api_key = re.sub(r'[^\x21-\x7e]', '', raw_key.strip())
else:
    api_key = None

if api_key:
    st.sidebar.write(f"Key-Länge: {len(api_key)}")

# Text-Cache im Session-State anlegen
if "extrahierte_texte" not in st.session_state:
    st.session_state.extrahierte_texte = {}

# Ordnernamen exakt wie im VS Code Explorer
KAMPAGNEN_ORDNER = "aktuelle_kampagne"
CHARAKTER_ORDNER = "spieler_Charaktere"


def lade_text_falls_noetig(pfad):
    """Liest ein PDF lokal aus und cached den reinen Text im Session-State."""
    if pfad in st.session_state.extrahierte_texte:
        return st.session_state.extrahierte_texte[pfad]

    dateiname = os.path.basename(pfad)
    with st.spinner(f"Extrahiere Text aus: {dateiname}..."):
        try:
            reader = PdfReader(pfad)
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as e:
            st.error(f"⚠️ Konnte {dateiname} nicht auslesen: {e}")
            return None

    if not text.strip():
        st.warning(f"⚠️ {dateiname} enthält keinen extrahierbaren Text (evtl. gescannt/Bild-basiert).")
        return None

    st.session_state.extrahierte_texte[pfad] = text
    st.write(f"Debug: {dateiname} → {len(text)} Zeichen extrahiert")
    return text


def sammle_kampagnen_texte(max_kapitel):
    """Läuft durch den Kampagnen-Ordner und gibt Player Guide + NUR das aktuell
    ausgewählte Kapitel zurück (nicht alle vorherigen)."""
    texte = []
    if not os.path.exists(KAMPAGNEN_ORDNER):
        st.error(f"Ordner '{KAMPAGNEN_ORDNER}' wurde nicht gefunden!")
        return texte

    for root, dirs, files in os.walk(KAMPAGNEN_ORDNER):
        for dateiname in files:
            if not dateiname.endswith(".pdf"):
                continue

            pfad = os.path.join(root, dateiname)
            passt = False
            dateiname_lower = dateiname.lower()

            if "playersguide" in dateiname_lower or "playerguide" in dateiname_lower:
                passt = True
            elif max_kapitel > 0 and f"chapter{max_kapitel}" in dateiname_lower:
                passt = True

            if passt:
                text = lade_text_falls_noetig(pfad)
                if text:
                    texte.append(f"--- Inhalt von {dateiname} ---\n{text}")

    return texte


def sammle_nur_kapitel_text(kapitel_nr):
    """Wie sammle_kampagnen_texte, aber OHNE den Player Guide - nur das reine Kapitel.
    Wird für NPC-Scan und -Import genutzt, da der Guide dort nicht gebraucht wird."""
    texte = []
    if not os.path.exists(KAMPAGNEN_ORDNER) or kapitel_nr <= 0:
        return texte

    for root, dirs, files in os.walk(KAMPAGNEN_ORDNER):
        for dateiname in files:
            if not dateiname.endswith(".pdf"):
                continue
            dateiname_lower = dateiname.lower()
            if f"chapter{kapitel_nr}" in dateiname_lower:
                pfad = os.path.join(root, dateiname)
                text = lade_text_falls_noetig(pfad)
                if text:
                    texte.append(f"--- Inhalt von {dateiname} ---\n{text}")
    return texte


def sammle_charakter_texte(namen_liste):
    """Liest ausgewählte Charakterbögen als Text ein. 
    Kann mit einzelnen Strings oder Listen umgehen."""
    if isinstance(namen_liste, str):
        namen_liste = [namen_liste]
        
    texte = []
    for name in namen_liste:
        if len(name) <= 1:
            continue
            
        pfad = os.path.join(CHARAKTER_ORDNER, f"{name}.pdf")
        text = lade_text_falls_noetig(pfad)
        if text:
            texte.append(f"--- Charakterbogen {name} ---\n{text}")
            
    return "\n\n".join(texte)


lokale_charaktere = []
if os.path.exists(CHARAKTER_ORDNER):
    lokale_charaktere = [os.path.splitext(f)[0] for f in os.listdir(CHARAKTER_ORDNER) if f.endswith(".pdf")]

st.sidebar.subheader("📈 Kampagnen-Fortschritt")
fortschritt = st.sidebar.radio(
    "Bei welchem Kapitel seid ihr aktuell?",
    options=["Nur Spieler-Leitfaden", "Kapitel 1", "Kapitel 2", "Kapitel 3", "Kapitel 4"],
    index=0
)

if st.sidebar.button("🗑️ Text-Cache leeren"):
    st.session_state.extrahierte_texte = {}
    st.sidebar.success("Cache geleert!")

fortschritt_stufen = {"Nur Spieler-Leitfaden": 0, "Kapitel 1": 1, "Kapitel 2": 2, "Kapitel 3": 3, "Kapitel 4": 4}

# Die Haupt-Tabs rendern (jetzt mit 4 Tabs inklusive Shinzos Shop)
tab1, tab2, tab3, tab4 = st.tabs([
    "📜 In-Character Tagebuch", 
    "⚔️ Quest-Logbuch", 
    "👤 NPC-Chronik", 
    "🏮 Shinzos Shop"
])

with tab1:
    tab_tagebuch.render_tab(api_key, fortschritt_stufen, fortschritt, lokale_charaktere, sammle_kampagnen_texte, sammle_charakter_texte)

with tab2:
    tab_quests.render_tab(api_key, fortschritt_stufen, fortschritt, sammle_nur_kapitel_text)

with tab3:
    tab_npcs.render_tab(api_key, fortschritt_stufen, fortschritt, sammle_kampagnen_texte, sammle_nur_kapitel_text)

with tab4:
    # Vorher: render_shop_tab()
    render_shop_tab(api_key)  # <-- Hier das api_key eintragen!