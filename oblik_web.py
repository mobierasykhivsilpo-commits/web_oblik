import streamlit as st
import pandas as pd
from PIL import Image
from pyzbar.pyzbar import decode
import io

# --- Налаштування ---
st.set_page_config(page_title="Мобільний Облік", page_icon="📦", layout="centered")

# --- Стилі ---
st.markdown("""
    <style>
    .price-tag { color: #2e7d32; font-weight: bold; font-size: 24px; }
    .big-name { font-size: 20px; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# --- Функції ---
def format_number(val):
    if pd.isna(val): return ""
    try: return str(int(round(float(val))))
    except: return str(val)

@st.cache_data
def load_data(uploaded_file):
    try:
        if uploaded_file.name.endswith('.xls'):
            df = pd.read_excel(uploaded_file, engine='xlrd', header=None)
        else:
            df = pd.read_excel(uploaded_file, engine='openpyxl', header=None)
        
        # Автопошук початку даних
        start_col = 0
        for col_idx in range(df.shape[1]):
            if not df.iloc[:10, col_idx].isnull().all():
                start_col = col_idx
                break
        
        mapping = {
            "name": start_col,
            "profit": start_col + 4,
            "price": start_col + 5,
            "art": start_col + 6,
            "code": start_col + 7
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

# --- Головне вікно ---
st.title("🌍 Сканер Товарів")

# 1. Завантаження бази
uploaded_file = st.file_uploader("📂 Завантажте файл Excel", type=['xls', 'xlsx'])

if uploaded_file:
    df = load_data(uploaded_file)
    if df is not None:
        st.success(f"В базі {len(df)} товарів")
        
        # 2. Вибір методу введення
        method = st.radio("Метод пошуку:", ["⌨️ Вручну", "📸 Камера"], horizontal=True)
        
        search_code = ""
        
        if method == "📸 Камера":
            img_file = st.camera_input("Зробіть фото штрихкоду")
            if img_file is not None:
                # Обробка фото
                image = Image.open(img_file)
                decoded_objects = decode(image)
                if decoded_objects:
                    search_code = decoded_objects[0].data.decode("utf-8")
                    st.info(f"Розпізнано код: {search_code}")
                else:
                    st.warning("Штрихкод не знайдено на фото. Спробуйте ближче.")
        else:
            search_code = st.text_input("Введіть код або назву")

        # 3. Пошук і відображення
        if search_code:
            query = search_code.lower().strip()
            mask = (
                df['Найменування'].str.lower().str.contains(query, na=False) |
                df['Код'].str.lower().str.contains(query, na=False) |
                df['Артикул'].str.lower().str.contains(query, na=False)
            )
            results = df[mask]
            
            st.divider()
            if not results.empty:
                for _, row in results.iterrows():
                    st.markdown(f"<div class='big-name'>{row['Найменування']}</div>", unsafe_allow_html=True)
                    c1, c2, c3 = st.columns(3)
                    c1.markdown(f"Ціна: <span class='price-tag'>{row['Ціна']}</span>", unsafe_allow_html=True)
                    c2.metric("Прибуток", row['Прибуток'])
                    c3.metric("Код", row['Код'])
                    st.divider()
            else:
                st.error("Товар не знайдено")