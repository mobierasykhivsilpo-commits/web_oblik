import streamlit as st
import pandas as pd
from PIL import Image
from pyzbar.pyzbar import decode
import os

# --- Налаштування ---
st.set_page_config(page_title="Облік", page_icon="📦", layout="centered", initial_sidebar_state="collapsed")

# --- CSS Стилі ---
st.markdown("""
    <style>
    .block-container { padding-top: 1rem; padding-bottom: 0rem; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    .product-card {
        background-color: #ffffff; padding: 15px; border-radius: 12px;
        margin-bottom: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); border: 1px solid #eee;
    }
    .product-name { font-size: 18px; font-weight: 700; color: #1f1f1f; margin-bottom: 4px; line-height: 1.3; }
    .product-code { font-size: 13px; color: #888; margin-bottom: 15px; font-family: monospace; }
    
    .stats-row { display: flex; justify-content: space-between; align-items: flex-end; border-top: 1px solid #f0f0f0; padding-top: 10px; }
    
    .profit-block { text-align: left; }
    .profit-label { font-size: 11px; text-transform: uppercase; color: #888; font-weight: 600; }
    .profit-val { font-size: 24px; font-weight: 800; color: #444; }
    
    .price-block { text-align: right; }
    .price-label { font-size: 11px; text-transform: uppercase; color: #888; font-weight: 600; }
    .price-val { font-size: 24px; font-weight: 800; color: #2e7d32; }
    
    button[kind="secondary"] { height: 2.5rem; margin-top: 0px !important; }
    div[data-testid="stCameraInput"] button { background-color: #2e7d32; color: white; border: none; }
    </style>
""", unsafe_allow_html=True)

# --- Функції ---
def format_number(val):
    if pd.isna(val): return ""
    try: return str(int(round(float(val))))
    except: return str(val)

@st.cache_data
def load_data(file_path_or_buffer):
    try:
        # Перевіряємо, чи це шлях до файлу (str) чи завантажений об'єкт
        if isinstance(file_path_or_buffer, str):
            engine = 'openpyxl' # Для локального файлу зазвичай xlsx
            header = None
        else:
            if file_path_or_buffer.name.endswith('.xls'):
                engine = 'xlrd'
            else:
                engine = 'openpyxl'
            header = None

        df = pd.read_excel(file_path_or_buffer, engine=engine, header=header)
        
        start_col = 0
        for col_idx in range(df.shape[1]):
            if not df.iloc[:10, col_idx].isnull().all():
                start_col = col_idx
                break
        
        mapping = {
            "name": start_col, "profit": start_col + 4,
            "price": start_col + 5, "art": start_col + 6, "code": start_col + 7
        }
        
        processed_data = []
        for _, row in df.iterrows():
            try:
                price = float(row.iloc[mapping['price']]) if pd.notna(row.iloc[mapping['price']]) else 0
                profit = float(row.iloc[mapping['profit']]) if pd.notna(row.iloc[mapping['profit']]) else 0
                code_val = str(row.iloc[mapping['code']])
                if code_val.endswith(".0"): code_val = code_val.replace(".0", "")
                
                processed_data.append({
                    "Найменування": str(row.iloc[mapping['name']]),
                    "Прибуток": format_number(profit),
                    "Ціна": format_number(price),
                    "Код": code_val,
                    "Артикул": str(row.iloc[mapping['art']])
                })
            except: continue
        return pd.DataFrame(processed_data)
    except Exception as e:
        return None

# --- UI ---
st.markdown("<h3 style='text-align: center; margin-bottom: 10px; margin-top: 0px;'>Облік</h3>", unsafe_allow_html=True)

if 'df' not in st.session_state:
    st.session_state.df = None

# ЛОГІКА АВТОЗАВАНТАЖЕННЯ
# Якщо файл data.xlsx є на сервері (в GitHub) - вантажимо його
default_file = "data.xlsx"

if st.session_state.df is None:
    # 1. Спробувати знайти файл на сервері
    if os.path.exists(default_file):
        # st.info(f"Знайдено базу: {default_file}") # Можна розкоментувати для налагодження
        df = load_data(default_file)
        if df is not None:
            st.session_state.df = df
            st.rerun()
    
    # 2. Якщо файлу немає, показати кнопку завантаження
    uploaded_file = st.file_uploader("Завантажити Excel", type=['xls', 'xlsx'], label_visibility="collapsed")
    if uploaded_file:
        df = load_data(uploaded_file)
        if df is not None:
            st.session_state.df = df
            st.rerun()

else:
    # Кнопка зміни файлу
    col_btn, col_empty = st.columns([1, 2])
    with col_btn:
        # Якщо файл був з сервера, кнопка дозволить завантажити свій
        if st.button("📂 Інший файл", type="secondary"):
            st.session_state.df = None
            st.rerun()

# --- Робоча зона ---
if st.session_state.df is not None:
    df = st.session_state.df
    
    tab_scan, tab_manual = st.tabs(["📹 Сканер", "⌨️ Пошук"])
    search_code = ""

    with tab_scan:
        img_buffer = st.camera_input("Scanner", label_visibility="collapsed")
        if img_buffer:
            image = Image.open(img_buffer)
            decoded = decode(image)
            if decoded:
                search_code = decoded[0].data.decode("utf-8")
            else:
                st.warning("Штрихкод не розпізнано.")

    with tab_manual:
        manual = st.text_input("Введіть код або назву", label_visibility="collapsed")
        if manual: search_code = manual

    if search_code:
        query = search_code.lower().strip()
        mask = (
            df['Найменування'].str.lower().str.contains(query, na=False) |
            df['Код'].str.lower().str.contains(query, na=False) |
            df['Артикул'].str.lower().str.contains(query, na=False)
        )
        results = df[mask]
        
        st.markdown("---")
        
        if not results.empty:
            for _, row in results.iterrows():
                html_card = f"""
<div class="product-card">
<div class="product-name">{row['Найменування']}</div>
<div class="product-code">Код: {row['Код']}</div>
<div class="stats-row">
<div class="profit-block"><div class="profit-label">Прибуток</div><div class="profit-val">{row['Прибуток']}</div></div>
<div class="price-block"><div class="price-label">Ціна</div><div class="price-val">{row['Ціна']} ₴</div></div>
</div>
</div>
"""
                st.markdown(html_card, unsafe_allow_html=True)
        else:
            st.error(f"Нічого не знайдено: '{search_code}'")
