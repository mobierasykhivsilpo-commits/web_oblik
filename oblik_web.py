import streamlit as st
import pandas as pd
from PIL import Image
import os
import glob
import re
from datetime import datetime
from streamlit_barcode_reader import barcode_reader

# --- Налаштування сторінки ---
st.set_page_config(page_title="Облік", page_icon="📦", layout="centered", initial_sidebar_state="collapsed")

# --- CSS Стилі (Твої оригінальні) ---
st.markdown("""
    <style>
    .block-container { padding-top: 1rem; padding-bottom: 0rem; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    button[data-baseweb="tab"] { flex: 1; width: 100%; justify-content: center; }
    
    .product-card {
        background-color: #ffffff; padding: 15px; border-radius: 12px;
        margin-bottom: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); border: 1px solid #eee;
    }
    .product-name { font-size: 18px; font-weight: 700; color: #1f1f1f; margin-bottom: 4px; line-height: 1.3; }
    .product-code { font-size: 13px; color: #888; margin-bottom: 15px; font-family: monospace; }
    
    .stats-row { display: flex; justify-content: space-between; align-items: flex-end; border-top: 1px solid #f0f0f0; padding-top: 10px; }
    .stat-label { font-size: 11px; text-transform: uppercase; color: #888; font-weight: 600; margin-bottom: 2px;}
    
    .purchase-block { text-align: left; width: 30%; }
    .purchase-val { font-size: 24px; font-weight: 800; color: #d32f2f; }
    
    .profit-block { text-align: center; width: 40%; }
    .profit-val { font-size: 24px; font-weight: 800; color: #444; }
    
    .price-block { text-align: right; width: 30%; }
    .price-val { font-size: 24px; font-weight: 800; color: #2e7d32; }
    
    button[kind="secondary"] { height: 2.5rem; margin-top: 0px !important; width: 100%; border: 1px solid #ddd; }
    </style>
""", unsafe_allow_html=True)

# --- Допоміжні функції (Твої оригінальні) ---
def extract_date_from_filename(filename: str) -> datetime:
    match = re.search(r'(\d{1,2})[.,-](?P<month>\d{1,2})(?:[.,-](?P<year>\d{2,4})?)', filename)
    if not match: return datetime.min
    day, month = int(match.group(1)), int(match.group('month'))
    year = int(match.group('year')) if match.group('year') else datetime.now().year
    if year < 100: year += 2000
    try: return datetime(year=year, month=month, day=day)
    except: return datetime.min

def find_best_file():
    patterns = ["Облік*.xls*", "oblik*.xls*", "Oblik*.xls*", "облік*.xls*", "обілк*.xls*", "data.xls*"]
    found_files = []
    for p in patterns: found_files.extend(glob.glob(p))
    found_files = list(set(found_files))
    if not found_files: return None
    try:
        found_files.sort(key=lambda f: extract_date_from_filename(f), reverse=True)
        return found_files[0]
    except: return found_files[0]

def format_number(val):
    if pd.isna(val): return ""
    try: return str(int(round(float(val))))
    except: return str(val)

@st.cache_data(show_spinner=False)
def load_data(file_path_or_buffer):
    try:
        engine = 'xlrd' if str(file_path_or_buffer).lower().endswith('.xls') else 'openpyxl'
        df = pd.read_excel(file_path_or_buffer, engine=engine, header=None)
        
        start_col = 0
        for col_idx in range(df.shape[1]):
            if not df.iloc[:10, col_idx].isnull().all():
                start_col = col_idx
                break
        
        mapping = {"name": start_col, "profit": start_col + 4, "price": start_col + 5, "art": start_col + 6, "code": start_col + 7}
        processed_data = []
        for _, row in df.iterrows():
            try:
                price = float(row.iloc[mapping['price']]) if pd.notna(row.iloc[mapping['price']]) else 0
                profit = float(row.iloc[mapping['profit']]) if pd.notna(row.iloc[mapping['profit']]) else 0
                code_val = str(row.iloc[mapping['code']]).replace(".0", "")
                processed_data.append({
                    "Найменування": str(row.iloc[mapping['name']]),
                    "Закуп": format_number(price - profit),
                    "Прибуток": format_number(profit),
                    "Ціна": format_number(price),
                    "Код": code_val,
                    "Артикул": str(row.iloc[mapping['art']])
                })
            except: continue
        return pd.DataFrame(processed_data)
    except Exception as e:
        st.error(f"Помилка: {e}")
        return None

# --- UI Логіка ---
st.markdown("<h3 style='text-align: center; margin-bottom: 10px; margin-top: 0px;'>Облік</h3>", unsafe_allow_html=True)

if 'df' not in st.session_state: st.session_state.df = None
if 'filename' not in st.session_state: st.session_state.filename = ""
if 'manual_mode' not in st.session_state: st.session_state.manual_mode = False

auto_file = find_best_file()
has_default = auto_file is not None

# Логіка завантаження (Твоя оригінальна)
if st.session_state.df is None:
    if has_default and not st.session_state.manual_mode:
        with st.spinner(f"Завантаження {auto_file}..."):
            df = load_data(auto_file)
        if df is not None:
            st.session_state.df, st.session_state.filename = df, f"📂 {auto_file}"
            st.rerun()
        else: st.session_state.manual_mode = True; st.rerun()

    uploaded_file = st.file_uploader("Оберіть файл Excel", type=['xls', 'xlsx'], label_visibility="collapsed")
    if uploaded_file:
        df = load_data(uploaded_file)
        if df is not None:
            st.session_state.df, st.session_state.filename = df, f"📂 {uploaded_file.name}"
            st.rerun()
else:
    if st.button(f"{st.session_state.filename}", type="secondary", use_container_width=True):
        st.session_state.df, st.session_state.manual_mode = None, True
        st.rerun()

# --- Робоча зона ---
if st.session_state.df is not None:
    df = st.session_state.df
    tab_scan, tab_manual = st.tabs(["📹 Сканер", "⌨️ Пошук"])
    search_code = ""

    with tab_scan:
        st.write("Наведіть камеру на штрихкод")
        # Новий професійний сканер (працює як відео)
        captured = barcode_reader()
        if captured:
            search_code = captured

    with tab_manual:
        manual = st.text_input("Введіть код або назву", label_visibility="collapsed", key="m_input")
        if manual: search_code = manual

    if search_code:
        query = str(search_code).lower().strip()
        mask = (
            df['Найменування'].str.lower().str.contains(query, na=False) |
            df['Код'].str.lower().str.contains(query, na=False) |
            df['Артикул'].str.lower().str.contains(query, na=False)
        )
        results = df[mask]
        st.markdown("---")
        if not results.empty:
            for _, row in results.iterrows():
                st.markdown(f"""
                <div class="product-card">
                    <div class="product-name">{row['Найменування']}</div>
                    <div class="product-code">Код: {row['Код']}</div>
                    <div class="stats-row">
                        <div class="purchase-block"><div class="stat-label">Закуп</div><div class="purchase-val">{row['Закуп']}</div></div>
                        <div class="profit-block"><div class="stat-label">Прибуток</div><div class="profit-val">{row['Прибуток']}</div></div>
                        <div class="price-block"><div class="stat-label">Ціна</div><div class="price-val">{row['Ціна']} ₴</div></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.error(f"Нічого не знайдено: '{search_code}'")
