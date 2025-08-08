# app.py
# ---------------------------------------------
# Aplikace pro vyšetřovatele požárů (Excel → DB ready)
# ---------------------------------------------

import os
import streamlit as st
import pandas as pd
from pathlib import Path

st.set_page_config(page_title="Aplikace pro vyšetřovatele požárů", layout="wide")

# ============ KONFIGURACE ============

def get_excel_path() -> str:
    """Vrátí cestu k Excelu — buď z secrets.toml, nebo výchozí."""
    try:
        return st.secrets["EXCEL_PATH"]  # použije secrets, pokud je k dispozici
    except Exception:
        return "data ptch.xlsx"  # výchozí soubor ve stejné složce jako app.py

PDF_DIR = Path("pdf")  # složka s normami (PDF)

# ============ DATA VRSTVA ============

@st.cache_data
def _load_excel_cached(path: str, sheet: str, mtime: float | None):
    """
    Interní cache-ovaná funkce.
    'mtime' drží cache v souladu s aktuálním Excelem.
    """
    return pd.read_excel(path, sheet_name=sheet)

def read_sheet(sheet: str) -> pd.DataFrame:
    """
    DNEŠEK: čte list z Excelu (jen pro čtení).
    ZÍTŘEK: přepiš na dotaz do DB (ponech stejné rozhraní).
    """
    path = get_excel_path()
    try:
        mtime = os.path.getmtime(path)  # invalidace cache při změně souboru
    except OSError:
        mtime = None
    return _load_excel_cached(path, sheet, mtime)

# ============ STAV A POMOCNÉ FUNKCE ============

if "zvolen_modul" not in st.session_state:
    st.session_state.zvolen_modul = None
if "aktivni_podmodul" not in st.session_state:
    st.session_state.aktivni_podmodul = None

def zpet_do_hlavniho_menu():
    st.session_state.zvolen_modul = None
    st.session_state.aktivni_podmodul = None
    st.rerun()

def vyhledat(df: pd.DataFrame, term: str) -> pd.DataFrame:
    """Fulltext přes všechny sloupce (case-insensitive)."""
    if not term:
        return df
    mask = df.apply(lambda r: r.astype(str).str.contains(term, case=False, na=False).any(), axis=1)
    return df[mask]

def read_pdf_bytes(path: Path) -> bytes:
    with open(path, "rb") as f:
        return f.read()

# ============ UI ============

st.title("🔎 Aplikace pro vyšetřovatele požárů 🔎")

# Info o zdroji dat
st.caption(f"Zdroj dat: **{get_excel_path()}**  •  (PTCH, INICIÁTORY)")

# Hlavní menu
if st.session_state.zvolen_modul is None:
    st.markdown("## 📂 Moduly")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔥 Požáry"):
            st.session_state.zvolen_modul = "pozary"
            st.rerun()
    with col2:
        if st.button("🧰 Podpora"):
            st.session_state.zvolen_modul = "podpora"
            st.rerun()

# Modul PODPORA – výběr podmodulu
elif st.session_state.zvolen_modul == "podpora" and st.session_state.aktivni_podmodul is None:
    st.markdown("## 🧰 Modul: Podpora")
    st.markdown("Vyber oblast:")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("📌 PTCH"):
            st.session_state.aktivni_podmodul = "PTCH"
            st.rerun()
        if st.button("💥 Iniciátory"):
            st.session_state.aktivni_podmodul = "INICIÁTORY"
            st.rerun()
    with col2:
        if st.button("📖 Normy"):
            st.session_state.aktivni_podmodul = "NORMY"
            st.rerun()
        st.button("📎 Jiné")

    st.markdown("---")
    cols = st.columns([1, 1, 2])
    with cols[0]:
        if st.button("🔙 Zpět do hlavního menu"):
            zpet_do_hlavniho_menu()
    with cols[1]:
        if st.button("🔄 Načíst znovu (vymazat cache)"):
            st.cache_data.clear()
            st.success("Cache vymazána. Načítám znovu…")
            st.rerun()

# Podmoduly PTCH a INICIÁTORY (Excel + vyhledávání)
elif st.session_state.aktivni_podmodul in ["PTCH", "INICIÁTORY"]:
    pod = st.session_state.aktivni_podmodul
    st.markdown(f"## 📑 {pod}")

    # Vyhledávání
    search = st.text_input(
        "🔍 Zadej hledaný text:",
        value="",
        placeholder="Např. dřevo",
        help="Vyhledává ve všech sloupcích (bez rozlišení velikosti písmen)."
    )

    # Data
    try:
        df = read_sheet(pod)
        df_filtered = vyhledat(df, search)

        # Výběr sloupců
        sloupce = st.multiselect(
            "Zobrazit sloupce",
            options=list(df_filtered.columns),
            default=list(df_filtered.columns),
        )

        st.dataframe(df_filtered[sloupce], use_container_width=True)
    except FileNotFoundError:
        st.error(f"Soubor **{get_excel_path()}** nebyl nalezen.")
    except ImportError as e:
        st.error(f"Chybí knihovna pro čtení Excelu: {e}. Nainstaluj `openpyxl`.")
    except Exception as e:
        st.error(f"Nepodařilo se načíst data: {e}")

    st.markdown("---")
    cols = st.columns([1, 1, 2])
    with cols[0]:
        if st.button("🔙 Zpět na výběr Podpora"):
            st.session_state.aktivni_podmodul = None
            st.rerun()
    with cols[1]:
        if st.button("🔄 Načíst znovu (vymazat cache)"):
            st.cache_data.clear()
            st.success("Cache vymazána. Načítám znovu…")
            st.rerun()

# Podmodul NORMY (PDF z lokální složky pdf/)
elif st.session_state.aktivni_podmodul == "NORMY":
    st.markdown("## 📖 Normy")

    normy = [
        ("ČSN 061008 – Požární bezpečnost tepelných zařízení (prostupy komínů)", PDF_DIR / "ČSN 061008.pdf"),
        ("ČSN 730872 – Ochrana staveb proti šíření požáru vzduchotechnických zařízením", PDF_DIR / "ČSN 730872.pdf"),
        ("ČSN 734230 – Krby s otevřeným a uzavíratelným ohništěm", PDF_DIR / "ČSN 734230.pdf"),
        ("ČSN 734201 – Komíny a kouřovody – Navrhování, provádění a připojování spotřebičů paliv", PDF_DIR / "ČSN 734201.pdf"),
    ]

    for nazev, path in normy:
        cols = st.columns([4, 1])
        with cols[0]:
            st.markdown(f"**{nazev}**")
        with cols[1]:
            try:
                data = read_pdf_bytes(path)
                st.download_button(
                    label="📄 Otevřít",
                    data=data,
                    file_name=path.name,
                    mime="application/pdf",
                    use_container_width=True
                )
            except FileNotFoundError:
                st.error(f"Soubor nenalezen: {path}")

        st.divider()

    st.markdown("---")
    if st.button("🔙 Zpět na výběr Podpora"):
        st.session_state.aktivni_podmodul = None
        st.rerun()

# Modul POŽÁRY (zatím prázdný)
elif st.session_state.zvolen_modul == "pozary":
    st.markdown("## 🔥 Modul: Požáry")
    st.info("Tento modul ještě není implementován.")
    st.markdown("---")
    if st.button("🔙 Zpět do hlavního menu"):
        zpet_do_hlavniho_menu()
