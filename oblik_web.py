import streamlit as st
import pandas as pd
from PIL import Image
from pyzbar.pyzbar import decode
import os
from datetime import datetime, timedelta

# --- Налаштування сторінки ---
st.set_page_config(page_title="Облік", page_icon="📦", layout="centered", initial_sidebar_state="collapsed")

# --- CSS Стилі ---
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
    
    /* Кнопки */
    button[kind="secondary"] { height: 2.5rem; margin-top: 0px !important; width: 100%; border: 1px solid #ddd; }
    div[data-testid="stCameraInput"] button { background-color: #2e7d32; color: white; border: none; }
    </style>
""", unsafe_allow_html=True)

# --- Функції ---
def format_number(val):
    if pd.isna(val): return ""
    try: return str(int(round(float(val))))
    except: return str(val)

@st.cache_data(show_spinner=False)
def load_data(file_path_or_buffer):
    try:
        if isinstance(file_path_or_buffer, str):
            engine = 'openpyxl'
            header = None
        else:
            if file_path_or_buffer.name.endswith('.xls'): engine = 'xlrd'
            else: engine = 'openpyxl'
            header = None

        df = pd.read_excel(file_path_or_buffer, engine=engine, header=header)
        
        start_col = 0
        found_data = False
        for col_idx in range(df.shape[1]):
            if not df.iloc[:10, col_idx].isnull().all():
                start_col = col_idx
                found_data = True
                break
        
        if not found_data:
            st.error("⚠️ У файлі не знайдено даних.")
            return None
        
        mapping = {
            "name": start_col, "profit": start_col + 4,
            "price": start_col + 5, "art": start_col + 6, "code": start_col + 7
        }
        
        if df.shape[1] <= mapping['code']:
             st.error(f"⚠️ Файл має нестандартну структуру.")
             return None

        processed_data = []
        for _, row in df.iterrows():
            try:
                price = float(row.iloc[mapping['price']]) if pd.notna(row.iloc[mapping['price']]) else 0
                profit = float(row.iloc[mapping['profit']]) if pd.notna(row.iloc[mapping['profit']]) else 0
                purchase = price - profit
                code_val = str(row.iloc[mapping['code']])
                if code_val.endswith(".0"): code_val = code_val.replace(".0", "")
                
                processed_data.append({
                    "Найменування": str(row.iloc[mapping['name']]),
                    "Закуп": format_number(purchase),
                    "Прибуток": format_number(profit),
                    "Ціна": format_number(price),
                    "Код": code_val,
                    "Артикул": str(row.iloc[mapping['art']])
                })
            except: continue
            
        if not processed_data:
            st.error("⚠️ Не вдалося розпізнати товари.")
            return None
            
        return pd.DataFrame(processed_data)

    except Exception as e:
        st.error(f"❌ Помилка: {e}")
        return None

# --- UI ---
st.markdown("<h3 style='text-align: center; margin-bottom: 10px; margin-top: 0px;'>Облік</h3>", unsafe_allow_html=True)

if 'df' not in st.session_state: st.session_state.df = None
if 'filename' not in st.session_state: st.session_state.filename = ""
if 'manual_mode' not in st.session_state: st.session_state.manual_mode = False

default_file = "data.xlsx"
has_default = os.path.exists(default_file)

# --- ЛОГІКА ЗАВАНТАЖЕННЯ ---
if st.session_state.df is None:
    # 1. АВТОЗАВАНТАЖЕННЯ (з датою)
    if has_default and not st.session_state.manual_mode:
        # Визначаємо дату зміни файлу
        try:
            timestamp = os.path.getmtime(default_file)
            # Додаємо +2 години (приблизно для Києва), бо сервер часто в UTC
            dt_obj = datetime.fromtimestamp(timestamp) + timedelta(hours=2) 
            date_str = dt_obj.strftime("%d.%m %H:%M")
            display_name = f"data.xlsx (від {date_str})"
        except:
            display_name = "data.xlsx (Авто)"

        with st.spinner("Завантаження бази..."):
            df = load_data(default_file)
            
        if df is not None:
            st.session_state.df = df
            st.session_state.filename = display_name
            st.rerun()
        else:
            st.session_state.manual_mode = True 
            st.rerun()
            
    # 2. РУЧНЕ ЗАВАНТАЖЕННЯ
    uploaded_file = st.file_uploader("Оберіть файл Excel", type=['xls', 'xlsx'], label_visibility="collapsed")
    
    if has_default and st.session_state.manual_mode:
        # Кнопка для повернення, якщо передумали
        if st.button("↩️ Використати файл з сервера", use_container_width=True):
            st.session_state.manual_mode = False
            st.rerun()

    if uploaded_file:
        with st.spinner("Обробка..."):
            df = load_data(uploaded_file)
        if df is not None:
            st.session_state.df = df
            st.session_state.filename = uploaded_file.name
            st.rerun()

else:
    # Кнопка для зміни файлу (показує назву і дату)
    if st.button(f"📂 {st.session_state.filename}", type="secondary", use_container_width=True):
        st.session_state.df = None
        st.session_state.filename = ""
        st.session_state.manual_mode = True
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
<div class="purchase-block">
<div class="stat-label">Закуп</div>
<div class="purchase-val">{row['Закуп']}</div>
</div>
<div class="profit-block">
<div class="stat-label">Прибуток</div>
<div class="profit-val">{row['Прибуток']}</div>
</div>
<div class="price-block">
<div class="stat-label">Ціна</div>
<div class="price-val">{row['Ціна']} ₴</div>
</div>
</div>
</div>
"""
                st.markdown(html_card, unsafe_allow_html=True)
        else:
            st.error(f"Нічого не знайдено: '{search_code}'")
