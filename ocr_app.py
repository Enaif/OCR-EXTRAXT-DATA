import os
os.makedirs("static", exist_ok=True)

import streamlit as st
from streamlit_drawable_canvas import st_canvas
import fitz
from PIL import Image, ImageOps, ImageDraw, ImageFont
import textwrap
import io
import re
import json
import numpy as np
import easyocr
import pandas as pd
from streamlit_lottie import st_lottie
import time
import gc
from multiprocessing.pool import ThreadPool

# ---------- CONFIG ----------
st.set_page_config(page_title="Vlozy - Simplifies Data Extraction",
                   layout="wide",
                   page_icon="favicon.png")

# Load OCR reader once
reader = easyocr.Reader(['en'], gpu=False)

zone_data_file = "zones_data.json"

# ---------- WEB3 STYLING ----------
st.markdown("""
<style>
.block-container { padding-top: 1.5rem !important; }
body { background: linear-gradient(135deg, #0f0c29, #302b63, #24243e); color: #ffffff; font-family: 'Courier New', monospace; }
h1, h2, h3, h4 { color: #00f6ff; text-shadow: 0px 0px 10px #00f6ff; }
.stButton>button { background: linear-gradient(90deg,#ff00cc,#3333ff); color: #ffffff; border: 2px solid #00f6ff; border-radius: 12px; font-weight: bold; transition: all 0.3s ease; }
.stButton>button:hover { box-shadow: 0 0 20px #00f6ff, 0 0 40px #ff00cc; transform: scale(1.05); }
.stTextInput>div>input, .stNumberInput>div>input { background-color: rgba(0,0,0,0.2); color: #ffffff; border: 2px solid #00f6ff; border-radius: 8px; padding: 5px 10px; font-weight: bold; }
input[type="file"]::file-selector-button { background-color: #0f0c29; color: #00f6ff; border: 2px solid #00f6ff; border-radius: 12px; padding: 5px 15px; font-weight: bold; cursor: pointer; transition: all 0.3s ease; }
input[type="file"]::file-selector-button:hover { background-color: #00f6ff; color: #0f0c29; border: 2px solid #00f6ff; }
.flash-box { padding: 15px; border: 1px solid #00f6ff; border-radius: 10px; background: rgba(0,246,255,0.1); box-shadow: 0 0 20px #00f6ff; text-align: justify; max-width: 700px; margin: 10px auto; line-height: 1.5; color: #00f6ff; font-family: 'Courier New', monospace; font-weight: normal; }
.side-alert { padding: 15px; border-radius: 10px; background: rgba(0,246,255,0.1); border: 1px solid #00f6ff; box-shadow: 0 0 20px #00f6ff; color: #00f6ff; font-weight: normal; text-align: left; margin-top: 20px; font-family: 'Courier New', monospace; }
</style>
""", unsafe_allow_html=True)

# ---------- TITLE ----------
st.markdown("<h1 style='text-align: center;'>🤖 Vlozy: Automate & Extract Data</h1>", unsafe_allow_html=True)

# --- Function to load a JSON file (Lottie) ---
def load_lottiefile(filepath: str):
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

# --- Function to convert any file to image ---
def load_file_as_image(uploaded_file):
    """Charge n'importe quel fichier (pdf, txt, image) et renvoie un objet PIL.Image"""
    file_name = uploaded_file.name.lower()
    file_bytes = uploaded_file.read()

    if file_name.endswith(".pdf"):
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        page = doc[0]
        pix = page.get_pixmap(matrix=fitz.Matrix(1,1))
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        del doc, page, pix
        gc.collect()
        return img

    elif file_name.endswith(".txt"):
        try:
            text = file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            text = file_bytes.decode("latin-1", errors="replace")

        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "C:/Windows/Fonts/arial.ttf",
            "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"
        ]
        font = None
        for path in font_paths:
            try:
                font = ImageFont.truetype(path, 17)
                break
            except:
                continue
        if font is None:
            font = ImageFont.load_default()

        margin = 20
        wrapped_lines = []
        for line in text.splitlines():
            wrapped_lines.extend(textwrap.wrap(line, width=100))
            if not line.strip():
                wrapped_lines.append("")

        dummy_img = Image.new("RGB", (1,1))
        dummy_draw = ImageDraw.Draw(dummy_img)
        max_width = max((dummy_draw.textbbox((0,0), l, font=font)[2] for l in wrapped_lines), default=0)
        max_width += 2*margin

        line_height = font.getbbox("Ag")[3] - font.getbbox("Ag")[1] + 5
        img_height = line_height * len(wrapped_lines) + 2*margin

        file_image = Image.new("RGB", (int(max_width), img_height), color="white")
        draw = ImageDraw.Draw(file_image)
        y = margin
        for line in wrapped_lines:
            draw.text((margin, y), line, font=font, fill="black")
            y += line_height

        del dummy_img, dummy_draw
        gc.collect()
        return file_image

    else:
        img = Image.open(io.BytesIO(file_bytes))
        return img

# --- OCR function with memory optimization ---
def ocr_on_zone(cropped_img):
    cropped_img = cropped_img.convert("L")  # grayscale to reduce memory
    result = reader.readtext(np.array(cropped_img), detail=0)
    del cropped_img
    gc.collect()
    return " ".join(result)

# --- Process single file ---
def process_single_file(uploaded_file, zones_to_apply):
    file_image = load_file_as_image(uploaded_file)
    extraction_dict = {}
    cropped_imgs = []

    for zone in zones_to_apply:
        x1, y1 = zone["left"], zone["top"]
        x2, y2 = x1 + zone["width"], y1 + zone["height"]
        cropped_imgs.append(file_image.crop((x1, y1, x2, y2)))

    # OCR with single-thread pool to limit CPU
    with ThreadPool(1) as pool:
        texts = pool.map(ocr_on_zone, cropped_imgs)

    for zone, text in zip(zones_to_apply, texts):
        text = re.sub(r'(?<=\d) (?=\d{2}$)', '.', text)
        extraction_dict[zone["name"]] = text

    extraction_dict["file_name"] = uploaded_file.name

    del file_image, cropped_imgs
    gc.collect()

    return extraction_dict

# --- Process batch with memory optimization ---
def process_batch(batch_files, zones_to_apply):
    if "batch_results" not in st.session_state:
        st.session_state.batch_results = []

    all_results = []
    with st.spinner("Processing files... this may take some time."):
        for uploaded_file in batch_files:
            result = process_single_file(uploaded_file, zones_to_apply)
            all_results.append(result)
            st.success(f"✅ {uploaded_file.name} processed")
            time.sleep(0.5)  # small delay to release CPU

    st.session_state.batch_results = all_results

    # Show download button only if results exist
    if st.session_state.batch_results:
        df_all = pd.DataFrame(st.session_state.batch_results)
        st.download_button(
            label="📥 Download results as CSV",
            data=df_all.to_csv(index=False).encode("utf-8"),
            file_name="batch_extract_results.csv",
            mime="text/csv"
        )

# ---------- STEP 0: UPLOAD + ANIMATION ----------
col_upload, col_animation = st.columns([1,1])

with col_upload:
    st.markdown("### 1️⃣ Upload your file")
    uploaded_file = st.file_uploader(
        "Upload your file here (single-page pdf or txt)", type=["pdf", "txt"]
    )

    # --- Checkbox to use existing zones JSON ---
    use_existing_zones = st.checkbox(
        "If you already have a JSON file with extraction zones, check this box."
    )

    zones_from_file = None
    if use_existing_zones:
        uploaded_zones_file = st.file_uploader(
            "Upload your zones JSON", type=["json"], key="zones_uploader"
        )
        if uploaded_zones_file:
            zones_from_file = json.load(uploaded_zones_file)
            st.success("✔️ Zones loaded successfully!")
            df_zones = pd.DataFrame(zones_from_file)
            st.dataframe(df_zones, use_container_width=True, hide_index=True)

            # ---------- STEP 4: BATCH EXTRACTION ----------
            st.markdown("### 2️⃣ Batch of files")
            batch_files = st.file_uploader(
                "Upload multiple files", type=["pdf", "txt"], accept_multiple_files=True
            )
            if batch_files:
                process_batch(batch_files, zones_from_file)

with col_animation:
    lottie_animation = load_lottiefile("animation.json")
    st_lottie(lottie_animation, speed=1, loop=True, quality="high", width=500)

# ---------- SI PAS DE JSON : FLUX CLASSIQUE ----------
if uploaded_file and not zones_from_file:
    file_image = load_file_as_image(uploaded_file)
    st.success("✔️ File loaded and a preview is displayed.")

    # Resize preview for canvas
    preview_img = file_image.copy()
    preview_img.thumbnail((800, 800))

    st.markdown("### 2️⃣ Define the zones")
    col1, col2 = st.columns([1,3])
    with col1:
        nb_zones = st.number_input("How many zones to define?", min_value=1, step=1)
        zone_names = [st.text_input(f"Zone {i+1} name", key=f"name_{i}") for i in range(nb_zones)]

    with col2:
        canvas_col, alert_col = st.columns([4,1])
        with canvas_col:
            canvas_result = st_canvas(
                fill_color="rgba(0,246,255,0.3)",
                stroke_width=2,
                stroke_color="#00f6ff",
                background_image=preview_img,
                update_streamlit=True,
                height=preview_img.height,
                width=preview_img.width,
                drawing_mode="rect",
                key="canvas"
            )

        with alert_col:
            if canvas_result.json_data and len(canvas_result.json_data["objects"]) == nb_zones:
                st.markdown('<div class="side-alert">✅ The number of rectangles matches the number of zone names.</div>', unsafe_allow_html=True)

    # ---------- STEP 3: VALIDATE & OCR ----------
    if 'canvas_result' in locals() and canvas_result.json_data:
        objects = canvas_result.json_data["objects"]
        if len(objects) == nb_zones:
            zones_to_save = []
            extraction_dict = {}
            for obj, name in zip(objects, zone_names):
                x1, y1 = int(obj['left']), int(obj['top'])
                x2, y2 = x1 + int(obj['width']), y1 + int(obj['height'])
                cropped_img = file_image.crop((x1, y1, x2, y2))
                cropped_img = ImageOps.expand(cropped_img, border=10, fill="white")
                text_str = ocr_on_zone(cropped_img)
                zones_to_save.append({
                    "name": name,
                    "left": x1, "top": y1,
                    "width": int(obj['width']),
                    "height": int(obj['height'])
                })
                extraction_dict[name] = text_str

            with open(zone_data_file, "w") as f:
                json.dump(zones_to_save, f)

            df = pd.DataFrame([extraction_dict])
            st.dataframe(df.style.set_properties(**{'text-align':'center'}), use_container_width=True, hide_index=True)

            zones_json = json.dumps(zones_to_save, indent=4)
            st.download_button(
                label="📥 Download zones configuration (JSON)",
                data=zones_json,
                file_name="extraction_zones.json",
                mime="application/json"
            )

    # ---------- STEP 4: BATCH EXTRACTION ----------
    apply_batch = st.checkbox("Perform bulk extraction using created zones")
    if apply_batch and 'zones_to_save' in locals():
        batch_files = st.file_uploader(
            "Upload multiple files", type=["pdf", "txt"], accept_multiple_files=True
        )
        if batch_files:
            process_batch(batch_files, zones_to_save)

