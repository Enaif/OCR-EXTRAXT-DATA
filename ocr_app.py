import os
import io
import re
import json
import fitz
import textwrap
import numpy as np
import pandas as pd
import streamlit as st
from PIL import Image, ImageOps, ImageDraw, ImageFont
from streamlit_lottie import st_lottie
from streamlit_drawable_canvas import st_canvas
import easyocr

# ---------- CONFIG ----------
st.set_page_config(
    page_title="Vlozy - Simplifies Data Extraction",
    layout="wide",
    page_icon="assets/favicon.png"
)

# Répertoires temporaires pour Render
os.makedirs("/tmp/vlozy", exist_ok=True)
zone_data_file = "/tmp/vlozy/zones_data.json"

# EasyOCR : stockage dans /tmp
reader = easyocr.Reader(
    ['en'],
    download_enabled=True,
    model_storage_directory="/tmp/easyocr"
)

# ---------- STYLING ----------
st.markdown(open("assets/style.css").read(), unsafe_allow_html=True)

# ---------- UTILS ----------
def load_lottiefile(filepath: str):
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

def load_file_as_image(uploaded_file):
    """Convertit PDF / TXT / Image en PIL.Image"""
    file_name = uploaded_file.name.lower()
    file_bytes = uploaded_file.read()

    if file_name.endswith(".pdf"):
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        page = doc[0]
        pix = page.get_pixmap()
        return Image.open(io.BytesIO(pix.tobytes("png")))

    elif file_name.endswith(".txt"):
        try:
            text = file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            text = file_bytes.decode("latin-1", errors="replace")

        font = None
        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        ]
        for path in font_paths:
            if os.path.exists(path):
                font = ImageFont.truetype(path, 17)
                break
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

        return file_image

    else:
        return Image.open(io.BytesIO(file_bytes))

def process_batch(batch_files, zones_to_apply):
    """Traite plusieurs fichiers en utilisant les zones OCR"""
    all_results = []
    with st.spinner("Processing files... this may take some time."):
        for uploaded_batch_file in batch_files:
            file_image = load_file_as_image(uploaded_batch_file)
            extraction_dict = {}
            for zone in zones_to_apply:
                x1, y1 = zone["left"], zone["top"]
                x2, y2 = x1 + zone["width"], y1 + zone["height"]
                cropped_img = file_image.crop((x1, y1, x2, y2))
                text_list = reader.readtext(
                    np.array(cropped_img.resize((cropped_img.width*2, cropped_img.height*2))),
                    detail=0
                )
                text_str = " ".join(text_list)
                text_str = re.sub(r'(?<=\d) (?=\d{2}$)', '.', text_str)
                extraction_dict[zone["name"]] = text_str
            extraction_dict["file_name"] = uploaded_batch_file.name
            all_results.append(extraction_dict)

    df_all = pd.DataFrame(all_results)
    st.download_button(
        label="📥 Download results as CSV",
        data=df_all.to_csv(index=False).encode("utf-8"),
        file_name="batch_extract_results.csv",
        mime="text/csv"
    )
    st.success("🎉 Batch processing completed!")

# ---------- UI ----------
st.markdown("<h1 style='text-align:center;'>🤖 Vlozy: Automate & Extract Data</h1>", unsafe_allow_html=True)

col_upload, col_animation = st.columns([1,1])

with col_upload:
    uploaded_file = st.file_uploader("Upload your file", type=["pdf", "txt"])
    use_existing_zones = st.checkbox("Use existing JSON zones")

    zones_to_apply = None
    if use_existing_zones:
        uploaded_zones_file = st.file_uploader("Upload zones JSON", type=["json"])
        if uploaded_zones_file:
            zones_to_apply = json.load(uploaded_zones_file)
            st.success("✔️ Zones configuration loaded successfully!")
            st.dataframe(pd.DataFrame(zones_to_apply), use_container_width=True, hide_index=True)

            batch_files = st.file_uploader("Upload multiple files for batch extraction", type=["pdf","txt"], accept_multiple_files=True)
            if batch_files:
                process_batch(batch_files, zones_to_apply)

with col_animation:
    lottie_animation = load_lottiefile("assets/animation.json")
    st_lottie(lottie_animation, speed=1, loop=True, quality="high", width=500)

# Si un fichier est uploadé et pas de JSON existant
if uploaded_file and not zones_to_apply:
    file_image = load_file_as_image(uploaded_file)
    st.success("✔️ File loaded. Preview below:")
    st.image(file_image, use_column_width=True)

    st.markdown("### 2️⃣ Define zones manually")
    nb_zones = st.number_input("How many zones to define?", min_value=1, step=1)
    zone_names = [st.text_input(f"Zone {i+1} name") for i in range(nb_zones)]

    if all(name.strip() != "" for name in zone_names):
        st.markdown("Draw rectangles on the image corresponding to each zone:")
        canvas_result = st_canvas(
            fill_color="rgba(0,246,255,0.3)",
            stroke_width=2,
            stroke_color="#00f6ff",
            background_image=file_image,
            update_streamlit=True,
            height=file_image.height,
            width=file_image.width,
            drawing_mode="rect",
            key="canvas",
        )

        if canvas_result.json_data and len(canvas_result.json_data["objects"]) == nb_zones:
            st.success("✅ Number of rectangles matches number of zones.")
            zones_to_apply = []
            extraction_dict = {}
            for obj, name in zip(canvas_result.json_data["objects"], zone_names):
                x1, y1 = int(obj['left']), int(obj['top'])
                x2, y2 = x1 + int(obj['width']), y1 + int(obj['height'])
                cropped_img = file_image.crop((x1, y1, x2, y2))
                cropped = ImageOps.expand(cropped_img, border=10, fill="white")
                text_list = reader.readtext(np.array(cropped.resize((cropped.width*2, cropped.height*2))), detail=0)
                text_str = " ".join(text_list)
                text_str = re.sub(r'(?<=\d) (?=\d{2}$)', '.', text_str)
                zones_to_apply.append({"name": name, "left": x1, "top": y1, "width": int(obj['width']), "height": int(obj['height'])})
                extraction_dict[name] = text_str

            # Sauvegarde zones dans /tmp
            with open(zone_data_file, "w") as f:
                json.dump(zones_to_apply, f)

            st.dataframe(pd.DataFrame(extraction_dict, index=[0]).style.set_properties(**{'text-align':'center'}), use_container_width=True, hide_index=True)
            zones_json = json.dumps(zones_to_apply, indent=4)
            st.download_button("📥 Download zones JSON", data=zones_json, file_name="extraction_zones.json", mime="application/json")

    # Batch extraction après zones manuelles
    apply_batch = st.checkbox("Apply these zones to multiple files")
    if apply_batch:
        batch_files = st.file_uploader("Upload multiple files for batch extraction", type=["pdf","txt"], accept_multiple_files=True)
        if batch_files:
            process_batch(batch_files, zones_to_apply)
