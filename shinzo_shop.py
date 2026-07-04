import streamlit as st
import json
import os
import difflib
import re
import urllib.parse

# ==============================================================================
# 📂 LOKALE KONFIGURATION (Liest direkt aus deinem Codespace-Ordner)
# ==============================================================================
LOKALER_ORDNER = "Items"  # Name deines Ordners im Codespace


def lade_lokale_item_liste():
    """Scannt den lokalen 'Items'-Ordner im Codespace nach JSON-Dateien."""
    try:
        if not os.path.exists(LOKALER_ORDNER):
            st.error(f"❌ Der Ordner '{LOKALER_ORDNER}' wurde im Codespace nicht gefunden!")
            return {}
            
        dateien = os.listdir(LOKALER_ORDNER)
        item_dateien = {}
        
        for dateiname in dateien:
            if dateiname.endswith(".json"):
                item_name_key = dateiname.replace(".json", "").lower().strip()
                item_dateien[item_name_key] = dateiname
                
        return item_dateien
    except Exception as e:
        st.error(f"❌ Fehler beim Scannen des lokalen Ordners: {e}")
        return {}


def lade_einzelnes_item_lokal(dateiname):
    """Lädt eine spezifische JSON-Datei direkt von der Codespace-Festplatte."""
    try:
        pfad = os.path.join(LOKALER_ORDNER, dateiname)
        with open(pfad, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        st.error(f"❌ Fehler beim Lesen der Datei {dateiname}: {e}")
        return None


def suche_items_in_lokaler_db(suchbegriff, kategorien_liste, api_key):
    """Durchsucht lokale Dateien extrem fehlertolerant. Findet Items selbst bei minimalen Treffern."""
    suchbegriff_clean = suchbegriff.lower().strip()
    if not suchbegriff_clean:
        return []

    verfuegbare_items = lade_lokale_item_liste()
    if not verfuegbare_items:
        return []

    # --- SCHRITT 1: KI-ÜBERSETZUNG ---
    such_begriffe_eng = []
    
    if not api_key:
        st.error("❌ Kein Gemini API-Key vorhanden!")
        return []

    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        
        prompt = f"""
        Du bist ein Pathfinder 2e Regeleperte. Ein Nutzer sucht nach Gegenständen mit der deutschen Beschreibung: "{suchbegriff}"
        Nenne mir die wichtigsten englischen Schlüsselwörter, nach denen man im Namen ODER in der Beschreibung suchen muss.
        
        Wichtig: Gib präzise Kombinationsbegriffe aus!
        - "Schwert mit Feuerschaden" -> sword, fire, flame, flaming, smoke, smoking
        - "Heiltrank für Untote" -> oil, unlife, undead, negative
        - "Heiltrank" -> potion, healing
        
        Antworte AUSSCHLIESSLICH mit den englischen Wörtern, getrennt durch Kommata. Keine Sätze, kein Markdown!
        """
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        
        raw_text = response.text if response.text else ""
        raw_words = raw_text.lower().replace("\n", "").strip().split(",")
        such_begriffe_eng = [w.strip() for w in raw_words if w.strip()]
    except Exception as e:
        such_begriffe_eng = []

    # Wichtig: Den gesäuberten Originalbegriff und gesplittete Wörter immer als Fallback hinzufügen!
    for part in suchbegriff_clean.split():
        if len(part) > 2 and part not in such_begriffe_eng:
            such_begriffe_eng.append(part)
    if suchbegriff_clean not in such_begriffe_eng:
        such_begriffe_eng.append(suchbegriff_clean)

    st.session_state["letzte_ki_begriffe"] = such_begriffe_eng

    # --- SCHRITT 2: TIEFENPRÜFUNG MIT SICHERHEITSNETZ ---
    treffer_mit_wertung = []

    for key, dateiname in verfuegbare_items.items():
        try:
            key_str = str(key).lower()
            
            # 1. Match im Dateinamen (Wir geben massig Punkte, wenn ein Wort vorkommt)
            namens_treffer = sum(5 for begriff in such_begriffe_eng if begriff in key_str)
            
            # 2. Match in der Beschreibung
            inhalts_treffer = 0
            item_daten = lade_einzelnes_item_lokal(dateiname)
            
            if item_daten and isinstance(item_daten, dict):
                system_data = item_daten.get("system", {})
                if isinstance(system_data, dict):
                    # Suche in Beschreibung
                    html_beschreibung = str(system_data.get("description", {}).get("value", "")).lower()
                    inhalts_treffer = sum(1 for begriff in such_begriffe_eng if begriff in html_beschreibung)
                    
                    # ZUSÄTZLICH: Wenn der echte Item-Name ("name") im JSON einen Begriff enthält, extra Punkte!
                    echter_name = str(item_daten.get("name", "")).lower()
                    namens_treffer += sum(5 for begriff in such_begriffe_eng if begriff in echter_name)

            gesamt_wertung = namens_treffer + inhalts_treffer

            # JEDER Treffer wird erlaubt, kein künstliches Aussperren mehr!
            if gesamt_wertung > 0:
                treffer_mit_wertung.append((gesamt_wertung, key, item_daten))
        except Exception:
            continue

    # Sortieren: Höchste Wertung nach oben
    treffer_mit_wertung.sort(key=lambda x: x[0], reverse=True)

    # --- FALLBACK: Wenn die KI-Suche 0 Treffer generiert hat, stumpf alles zeigen was den Text enthält ---
    if not treffer_mit_wertung:
        for key, dateiname in verfuegbare_items.items():
            if any(b in str(key).lower() for b in such_begriffe_eng):
                item_daten = lade_einzelnes_item_lokal(dateiname)
                if item_daten:
                    treffer_mit_wertung.append((1, key, item_daten))

    gefundene_items = []

    # --- SCHRITT 3: FORMATIERUNG ---
    for wertung, key, item_daten in treffer_mit_wertung:
        if not item_daten:
            continue
        try:
            system_data = item_daten.get("system", {})
            price_obj = system_data.get("price", {}).get("value", {})
            
            if isinstance(price_obj, dict) and price_obj:
                preis_str = ", ".join([f"{v} {k.upper()}" for k, v in price_obj.items()])
            else:
                preis_str = "0 GP"

            html_beschreibung = system_data.get("description", {}).get("value", "Keine Beschreibung.")
            clean_beschreibung = re.sub(r'<[^<]+?>', '', str(html_beschreibung))
            clean_beschreibung = re.sub(r'@UUID\[[^\]]+\]', '', clean_beschreibung)

            foundry_cat = str(system_data.get("category", "")).lower()
            zugewiesene_kat = kategorien_liste[6]
            
            if "potion" in foundry_cat or "elixir" in foundry_cat or "oil" in str(key):
                zugewiesene_kat = kategorien_liste[2]
            elif "weapon" in foundry_cat or "sword" in str(key):
                zugewiesene_kat = kategorien_liste[0]
            elif "armor" in foundry_cat or "shield" in foundry_cat:
                zugewiesene_kat = kategorien_liste[1]

            eng_name = item_daten.get("name", "Unknown Item")
            
            gefundene_items.append({
                "Name": eng_name,
                "Englischer_Name": eng_name,
                "Kategorie": zugewiesene_kat,
                "Preis": preis_str,
                "Beschreibung": clean_beschreibung.strip(),
                "Link": f"https://2e.aonprd.com/Search.aspx?q={urllib.parse.quote(str(eng_name))}",
                "Wertung": int(wertung)
            })
        except Exception:
            continue

    return gefundene_items


# ==============================================================================
# 💾 PERSISTENTE SPEICHERUNG (Speichert das Shop-Inventar auf der Festplatte)
# ==============================================================================
INVENTAR_DATEI = "shop_inventar.json"

def lade_gespeichertes_inventar():
    """Lädt das Shop-Inventar aus der JSON-Datei, falls vorhanden."""
    if os.path.exists(INVENTAR_DATEI):
        try:
            with open(INVENTAR_DATEI, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            st.error(f"Fehler beim Laden des persistenten Inventars: {e}")
    return {}

def speichere_inventar(inventar):
    """Speichert das aktuelle Shop-Inventar permanent auf die Festplatte."""
    try:
        with open(INVENTAR_DATEI, "w", encoding="utf-8") as f:
            json.dump(inventar, f, ensure_ascii=False, indent=4)
    except Exception as e:
        st.error(f"Fehler beim Speichern des Inventars: {e}")


def render_shop_tab(api_key=None):
    """Baut die Benutzeroberfläche für den Webshop auf (mit permanenter Speicherung)."""
    st.subheader("🏮 Shinzos Kuriositäten & Warenlager")
    st.write("*Verwalte das Inventar permanent. Die Daten bleiben auch nach dem Schließen der Seite gespeichert!*")

    KATEGORIEN = [
        "⚔️ Waffen",
        "🛡️ Rüstungen & Schilde",
        "🧪 Alchemistische Gegenstände (Elixiere, Bomben)",
        "✨ Magische Gegenstände (Ringe, Amulette)",
        "📜 Schriftrollen & Zauberstäbe",
        "🌿 Kräuter & Medizin",
        "🎒 Abenteuerausrüstung & Werkzeuge",
        "💎 Wertgegenstände & Antiquitäten"
    ]

    # Lade Inventar aus Datei, falls es noch nicht im Session State existiert
    if "shop_inventar" not in st.session_state:
        st.session_state.shop_inventar = lade_gespeichertes_inventar()

    with st.expander("➕ Gegenstand hinzufügen (Codespace-Suche oder Manuell)", expanded=False):
        tab_ki, tab_manuell = st.tabs(["📦 Codespace Gegenstandssuche", "✍️ Manuell erstellen"])
        
        with tab_ki:
            st.markdown("### Lokaler Gegenstands-Finder (Aus deinem 'Items'-Ordner)")
            ki_suchbegriff = st.text_input("Welches Item suchst du?", placeholder="z.B. heiltrank, schwert mit feuer...")
            
            if st.button("🔮 In lokalen Codespace-Dateien suchen", use_container_width=True):
                if not ki_suchbegriff.strip():
                    st.warning("⚠️ Bitte gib zuerst einen Suchbegriff ein.")
                else:
                    st.session_state["aktuelle_ki_ergebnisse"] = None
                    
                    with st.spinner("🔮 KI übersetzt Begriff und filtert lokale JSONs..."):
                        gefundene_liste = suche_items_in_lokaler_db(ki_suchbegriff, KATEGORIEN, api_key=api_key)
                        
                    if gefundene_liste:
                        st.session_state["aktuelle_ki_ergebnisse"] = gefundene_liste
                    else:
                        st.info(f"Keine passenden Gegenstände für '{ki_suchbegriff}' im 'Items'-Ordner gefunden.")
                        st.session_state["aktuelle_ki_ergebnisse"] = None
                        
            if "aktuelle_ki_ergebnisse" in st.session_state and st.session_state["aktuelle_ki_ergebnisse"]:
                st.markdown("---")
                st.markdown(f"### 🔍 Gefundene Treffer im Ordner:")
                
                ergebnisse = st.session_state["aktuelle_ki_ergebnisse"]
                scores = [int(i["Wertung"]) for i in ergebnisse if "Wertung" in i]
                max_score = max(scores) if scores else 1
                
                perfekte_treffer = [i for i in ergebnisse if i.get("Wertung", 0) >= max(3, max_score - 1)]
                gute_treffer = [i for i in ergebnisse if 2 <= i.get("Wertung", 0) < max(3, max_score - 1)]
                vage_treffer = [i for i in ergebnisse if i.get("Wertung", 0) <= 1]
                
                tab_titel = [
                    f"🎯 Beste Treffer ({len(perfekte_treffer)})", 
                    f"👍 Gute Treffer ({len(gute_treffer)})", 
                    f"🔍 Vage Treffer ({len(vage_treffer)})"
                ]
                
                res_tab1, res_tab2, res_tab3 = st.tabs(tab_titel)
                
                def render_item_liste(item_liste, tab_id):
                    if not item_liste:
                        st.info("Keine Gegenstände in dieser Gruppe gefunden.")
                        return
                    for idx, ki_item in enumerate(item_liste):
                        with st.container(border=True):
                            col_item_info, col_item_btn = st.columns([3, 1])
                            with col_item_info:
                                st.markdown(f"#### {ki_item['Name']}")
                                st.markdown(f"**Kategorie:** {ki_item['Kategorie']} | **Preis:** `{ki_item['Preis']}`")
                                st.info(ki_item['Beschreibung'])
                                
                            with col_item_btn:
                                st.write("")
                                if st.button("📥 In Shop stellen", key=f"add_ki_{ki_item['Name']}_{tab_id}_{idx}", type="primary", use_container_width=True):
                                    # Item im State speichern
                                    st.session_state.shop_inventar[ki_item['Name']] = {
                                        "Englischer_Name": ki_item['Englischer_Name'],
                                        "Kategorie": ki_item['Kategorie'],
                                        "Preis": ki_item['Preis'],
                                        "Beschreibung": ki_item['Beschreibung'],
                                        "Link": ki_item['Link']
                                    }
                                    # Permanent auf Festplatte sichern
                                    speichere_inventar(st.session_state.shop_inventar)
                                    st.toast(f"'{ki_item['Name']}' dauerhaft gespeichert!")

                with res_tab1: render_item_liste(perfekte_treffer, "tab1")
                with res_tab2: render_item_liste(gute_treffer, "tab2")
                with res_tab3: render_item_liste(vage_treffer, "tab3")

        with tab_manuell:
            with st.form("neues_item_form", clear_on_submit=True):
                st.markdown("### Details des neuen Gegenstands")
                neuer_name = st.text_input("Gegenstandsname (Deutsch):")
                neuer_eng_name = st.text_input("Englischer Name (Optional):")
                col_kat, col_preis = st.columns(2)
                with col_kat: neue_kat = st.selectbox("Kategorie wählen:", KATEGORIEN)
                with col_preis: neuer_preis = st.text_input("Preis / Wert:")
                neue_beschreibung = st.text_area("Beschreibung & Effekte:")
                submit_btn = st.form_submit_button("Gegenstand manuell in den Shop stellen")
                
                if submit_btn:
                    if not neuer_name.strip() or not neuer_preis.strip():
                        st.error("❌ Name und Preis werden benötigt.")
                    else:
                        eng_name_wert = neuer_eng_name.strip() if neuer_eng_name.strip() else neuer_name.strip()
                        st.session_state.shop_inventar[neuer_name.strip()] = {
                            "Englischer_Name": eng_name_wert,
                            "Kategorie": neue_kat,
                            "Preis": neuer_preis.strip(),
                            "Beschreibung": neue_beschreibung.strip() if neue_beschreibung.strip() else "Keine Beschreibung.",
                            "Link": f"https://2e.aonprd.com/Search.aspx?q={urllib.parse.quote(eng_name_wert)}"
                        }
                        speichere_inventar(st.session_state.shop_inventar)
                        st.success(f"✔️ '{neuer_name}' dauerhaft hinzugefügt!")
                        st.rerun()

    st.write("---")
    inventar = st.session_state.shop_inventar
    if not inventar:
        st.info("🏮 Shinzos Shop ist aktuell noch leer. Benutze den Bereich oben, um Waren aus deinem Codespace hinzuzufügen!")
        return

    # --- INVENTAR FILTER & LISTE ---
    col_search, col_filter = st.columns([2, 1])
    with col_search:
        suchbegriff = st.text_input("🔍 Vorhandenes Item im Shop filtern:", placeholder="Name eingeben...").strip().lower()
    with col_filter:
        gewaehlte_kat = st.selectbox("📁 Kategorie filtern:", ["Alle"] + KATEGORIEN)

    st.write("---")
    header_col1, header_col2, header_col3, header_col4, header_col5 = st.columns([3, 2, 1.5, 1, 1])
    with header_col1: st.markdown("**📦 Gegenstand**")
    with header_col2: st.markdown("**📁 Kategorie**")
    with header_col3: st.markdown("**💰 Preis**")
    with header_col4: st.markdown("**ℹ️ Info**")
    with header_col5: st.markdown("**🗑️ Löschen**")
    st.write("---")

    for item_name, details in list(inventar.items()):
        if suchbegriff and suchbegriff not in item_name.lower(): continue
        if gewaehlte_kat != "Alle" and details["Kategorie"] != gewaehlte_kat: continue

        row_col1, row_col2, row_col3, row_col4, row_col5 = st.columns([3, 2, 1.5, 1, 1])
        with row_col1:
            st.markdown(f"**{item_name}**")
            st.markdown(f"<small style='color: gray;'>({details.get('Englischer_Name', '')})</small>", unsafe_allow_html=True)
        with row_col2: 
            st.write(details["Kategorie"])
        with row_col3: 
            st.markdown(f"`{details['Preis']}`")
        with row_col4:
            if st.button("Ansehen", key=f"btn_view_{item_name}", use_container_width=True):
                zeige_item_details(item_name, details)
        with row_col5:
            # Direkter Löschen-Button in der Zeile für schnelle Verwaltung
            if st.button("❌", key=f"btn_del_row_{item_name}", help="Aus dem Shop löschen", use_container_width=True):
                del st.session_state.shop_inventar[item_name]
                speichere_inventar(st.session_state.shop_inventar)
                st.toast(f"'{item_name}' gelöscht!")
                st.rerun()


@st.dialog("🔮 Gegenstands-Details")
def zeige_item_details(name, details):
    st.markdown(f"### {name}")
    st.markdown(f"**Englischer Name:** `{details.get('Englischer_Name', '')}`")
    st.markdown(f"**Kategorie:** {details['Kategorie']}")
    st.markdown(f"**Wert:** `{details['Preis']}`")
    st.write("---")
    st.markdown("**Beschreibung:**")
    st.info(details["Beschreibung"])
    
    if "Link" in details:
        st.markdown(f"[📖 Offizieller Archives of Nethys Eintrag]({details['Link']})")
        
    st.write("---")
    if st.button("🗑️ Aus dem Shop entfernen", type="primary", use_container_width=True):
        if name in st.session_state.shop_inventar:
            del st.session_state.shop_inventar[name]
            speichere_inventar(st.session_state.shop_inventar)
            st.rerun()
    if st.button("Schließen", use_container_width=True):
        st.rerun()