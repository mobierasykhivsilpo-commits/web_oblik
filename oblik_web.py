import streamlit as st
import pandas as pd
import cv2
import numpy as np
from pyzbar.pyzbar import decode
from PIL import Image

# --- НАЛАШТУВАННЯ СТОРІНКИ ---
st.set_page_config(page_title="Web Oblik", page_icon="📦")

# --- ФУНКЦІЇ ОБРОБКИ ЗОБРАЖЕНЬ ---

def decode_barcode_with_preprocessing(image_file):
    """
    Розпізнає штрихкод, намагаючись покращити зображення, 
    якщо з першого разу не вдалося (для бюджетних камер).
    """
    try:
        # Завантаження зображення
        if isinstance(image_file, Image.Image):
            pil_image = image_file
        else:
            pil_image = Image.open(image_file)

        # Конвертація в формат для OpenCV
        opencv_image = np.array(pil_image.convert('RGB'))
        # RGB -> BGR
        opencv_image = cv2.cvtColor(opencv_image, cv2.COLOR_RGB2BGR)

        # СПРОБА 1: Оригінал
        decoded = decode(opencv_image)
        if decoded: return decoded[0].data.decode('utf-8')

        # СПРОБА 2: Відтінки сірого
        gray = cv2.cvtColor(opencv_image, cv2.COLOR_BGR2GRAY)
        decoded = decode(gray)
        if decoded: return decoded[0].data.decode('utf-8')

        # СПРОБА 3: Підвищення контрасту (CLAHE)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        contrast = clahe.apply(gray)
        decoded = decode(contrast)
        if decoded: return decoded[0].data.decode('utf-8')

        # СПРОБА 4: Адаптивна бінаризація (Чорно-біле)
        thresh = cv2.adaptiveThreshold(
            contrast, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 11, 2
        )
        decoded = decode(thresh)
        if decoded: return decoded[0].data.decode('utf-8')

    except Exception as e:
        st.error(f"Помилка обробки фото: {e}")
        
    return None

# --- ЗАВАНТАЖЕННЯ ДАНИХ ---

@st.cache_data
def load_data(file):
    try:
        if file.name.endswith('.xls'):
            df = pd.read_excel(file, engine='xlrd')
        else:
            df = pd.read_excel(file, engine='openpyxl')
        
        # Приведення колонок до стрічкового типу для пошуку
        # ПРИМІТКА: Перевір, щоб назви колонок тут збігалися з твоїм Excel!
        # Я використовую стандартні назви, зміни їх якщо треба.
        # Наприклад, якщо у тебе "Код товару", зміни 'Код' на 'Код товару'
        
        # Конвертуємо всі коди в стрічку, прибираючи .0 якщо є
        if 'Код' in df.columns:
            df['Код'] = df['Код'].astype(str).str.replace(r'\.0$', '', regex=True)
            
        return df
    except Exception as e:
        st.error(f"Не вдалося відкрити файл: {e}")
        return None

# --- UI ВІДОБРАЖЕННЯ ТОВАРУ ---

def show_product_card(product_row):
    """Гарне відображення інформації про товар"""
    st.markdown("---")
    
    # Отримуємо дані з рядка (використовуємо .get для безпеки)
    # Зміни ключі ['...'], якщо твої колонки називаються інакше
    name = product_row.get('Найменування', 'Назва не вказана')
    code = product_row.get('Код', '---')
    price_sell = product_row.get('Ціна', 0)
    price_buy = product_row.get('Закуп', 0) # Або 'Собівартість'
    
    # Обчислюємо прибуток, якщо його немає в таблиці
    if 'Прибуток' in product_row:
        profit = product_row['Прибуток']
    else:
        try:
            profit = float(price_sell) - float(price_buy)
        except:
            profit = 0

    st.subheader(name)
    st.caption(f"Код: {code}")

    # Використовуємо колонки для красивого відображення цифр
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(label="ЗАКУП", value=f"{price_buy}")
    
    with col2:
        st.metric(label="ПРИБУТОК", value=f"{profit}")
    
    with col3:
        st.metric(label="ЦІНА", value=f"{price_sell} ₴")
        
    st.success("Товар знайдено!")

# --- ГОЛОВНА ЛОГІКА ПРОГРАМИ ---

st.title("Облік")

# 1. Завантаження бази даних
db_file = st.file_uploader("📂 Завантаж файл бази (Excel)", type=['xls', 'xlsx'])

if db_file:
    df = load_data(db_file)
    
    if df is not None:
        st.info(f"База завантажена: {len(df)} товарів")
        
        # Вкладки
        tab1, tab2 = st.tabs(["📹 Сканер", "⌨️ Пошук"])

        # --- ВКЛАДКА 1: СКАНЕР ---
        with tab1:
            st.write("Зроби фото штрихкоду або завантаж зображення")
            
            # Вибір джерела: Камера або Файл
            input_method = st.radio("Джерело:", ["Камера", "Завантажити фото"], horizontal=True, label_visibility="collapsed")
            
            img_input = None
            
            if input_method == "Камера":
                img_input = st.camera_input("Камера")
            else:
                img_input = st.file_uploader("Вибери фото", type=['jpg', 'png', 'jpeg'])

            if img_input:
                with st.spinner('Обробка зображення...'):
                    # Викликаємо нашу покращену функцію
                    barcode = decode_barcode_with_preprocessing(img_input)
                
                if barcode:
                    st.success(f"Зчитано код: {barcode}")
                    
                    # Пошук в базі
                    # Шукаємо точний збіг
                    result = df[df['Код'] == barcode]
                    
                    if not result.empty:
                        # Беремо перший знайдений рядок (як словник)
                        show_product_card(result.iloc[0])
                    else:
                        st.warning(f"Товар з кодом {barcode} не знайдено в базі.")
                else:
                    st.error("Штрихкод не розпізнано. Спробуй наблизити камеру або покращити світло.")

        # --- ВКЛАДКА 2: ПОШУК ---
        with tab2:
            search_query = st.text_input("Введи назву або код товару")
            
            if search_query:
                # Пошук по Коду АБО по Назві (без врахування регістру)
                # Конвертуємо все в стрічки для пошуку
                mask_code = df['Код'].astype(str).str.contains(search_query, na=False)
                mask_name = df['Найменування'].astype(str).str.contains(search_query, case=False, na=False)
                
                search_results = df[mask_code | mask_name]
                
                if not search_results.empty:
                    st.write(f"Знайдено: {len(search_results)}")
                    # Якщо один результат - показуємо картку
                    if len(search_results) == 1:
                        show_product_card(search_results.iloc[0])
                    else:
                        # Якщо багато - показуємо таблицю
                        st.dataframe(search_results[['Код', 'Найменування', 'Ціна']])
                else:
                    st.warning("Нічого не знайдено.")

else:
    st.warning("Будь ласка, завантаж файл Excel для початку роботи.")
