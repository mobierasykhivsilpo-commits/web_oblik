import streamlit as st
import pandas as pd
from PIL import Image
from pyzbar.pyzbar import decode
import io

# --- Налаштування сторінки ---
st.set_page_config(page_title="Облік", page_icon="📦", layout="centered")

# --- CSS Стилі (Дизайн) ---
st.markdown("""
    <style>
    /* Приховуємо стандартне меню зверху для чистоти */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Стилі для картки товару */
    .product-card {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 10px;
        border: 1px solid #e0e0e0;
    }
    .product-name {
        font-size: 20px;
        font-weight: bold;
        color: #1f1f1f;
        margin-bottom: 2px;
        line-height: 1.2;
    }
    .product-code {
        font-size: 14px;
        color: #666;
        margin-bottom: 12px;
        font-family: monospace;
    }
    .stats-row {
        display: flex;
        justify-content: space-between;
        align-items: flex-end;
    }
    .profit-block {
        text-align: left;
    }
    .profit-label {
        font-size: 12px;
        color: #555;
    }
    .profit-val {
        font-size: 18px;
        font-weight: bold;
        color: #333;
    }
    .price-block {
        text-align: right;
    }
    .price-label {
        font-size: 12px;
        color: #555;
    }
    .price-val {
        font-size: 24px;
        font-weight: bold;
        color: #2e7d32; /* Зелений колір */
    }
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

# --- Головний екран ---
st.title("Облік") # Мінімалістичний заголовок

uploaded_file = st.file_uploader("Завантажити Excel", type=['xls', 'xlsx'], label_visibility="collapsed")

if uploaded_file:
    df = load_data(uploaded_file)
    if df is not None:
        st.success(f"База: {len(df)} поз.", icon="✅")
        
        # Перемикач режимів (компактний)
        mode = st.radio("Режим:", ["⌨️ Вручну", "📸 Камера"], horizontal=True, label_visibility="collapsed")
        
        search_code = ""
        
        if mode == "📸 Камера":
            img_file = st.camera_input("Фото штрихкоду", label_visibility="collapsed")
            if img_file:
                image = Image.open(img_file)
                decoded_objects = decode(image)
                if decoded_objects:
                    search_code = decoded_objects[0].data.decode("utf-8")
                else:
                    st.warning("Код не знайдено")
        else:
            search_code = st.text_input("Пошук", placeholder="Введіть код або назву")

        # --- Результати ---
        if search_code:
            query = search_code.lower().strip()
            mask = (
                df['Найменування'].str.lower().str.contains(query, na=False) |
                df['Код'].str.lower().str.contains(query, na=False) |
                df['Артикул'].str.lower().str.contains(query, na=False)
            )
            results = df[mask]
            
            st.write("") # Відступ
            
            if not results.empty:
                for _, row in results.iterrows():
                    # HTML-верстка картки товару
                    html_card = f"""
                    <div class="product-card">
                        <div class="product-name">{row['Найменування']}</div>
                        <div class="product-code">Код: {row['Код']}</div>
                        
                        <div class="stats-row">
                            <div class="profit-block">
                                <div class="profit-label">Прибуток</div>
                                <div class="profit-val">{row['Прибуток']}</div>
                            </div>
                            <div class="price-block">
                                <div class="price-label">Ціна</div>
                                <div class="price-val">{row['Ціна']} ₴</div>
                            </div>
                        </div>
                    </div>
                    """
                    st.markdown(html_card, unsafe_allow_html=True)
            else:
                st.error("Товар не знайдено")
