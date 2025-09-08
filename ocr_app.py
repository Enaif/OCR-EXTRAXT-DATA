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

# ---------- CONFIG ----------
st.set_page_config(page_title="Vlozy - Simplifies Data Extraction",
                   layout="wide",
                   page_icon="favicon.png")
reader = easyocr.Reader(['en'])
zone_data_file = "zones_data.json"

# ---------- WEB3 STYLING ----------
st.markdown("""
<style>
.block-container {
        padding-top: 1.5rem !important;
    }
body {
    background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
    color: #ffffff;
    font-family: 'Courier New', monospace;
}
h1, h2, h3, h4 {
    color: #00f6ff;
    text-shadow: 0px 0px 10px #00f6ff;
}
.stButton>button {
    background: linear-gradient(90deg,#ff00cc,#3333ff);
    color: #ffffff;
    border: 2px solid #00f6ff;
    border-radius: 12px;
    font-weight: bold;
    transition: all 0.3s ease;
}
.stButton>button:hover {
    box-shadow: 0 0 20px #00f6ff, 0 0 40px #ff00cc;
    transform: scale(1.05);
}
.stTextInput>div>input, .stNumberInput>div>input {
    background-color: rgba(0,0,0,0.2);
    color: #ffffff;
    border: 2px solid #00f6ff;
    border-radius: 8px;
    padding: 5px 10px;
    font-weight: bold;
}
input[type="file"]::file-selector-button {
    background-color: #0f0c29;
    color: #00f6ff;
    border: 2px solid #00f6ff;
    border-radius: 12px;
    padding: 5px 15px;
    font-weight: bold;
    cursor: pointer;
    transition: all 0.3s ease;
}
input[type="file"]::file-selector-button:hover {
    background-color: #00f6ff;
    color: #0f0c29;
    border: 2px solid #00f6ff;
}
.flash-box {
    padding: 15px;
    border: 1px solid #00f6ff;
    border-radius: 10px;
    background: rgba(0,246,255,0.1);
    box-shadow: 0 0 20px #00f6ff;
    text-align: justify;
    max-width: 700px;
    margin: 10px auto;
    line-height: 1.5;
    color: #00f6ff;
    font-family: 'Courier New', monospace;
    font-weight: normal;
}
.side-alert {
    padding: 15px;
    border-radius: 10px;
    background: rgba(0,246,255,0.1);
    border: 1px solid #00f6ff;
    box-shadow: 0 0 20px #00f6ff;
    color: #00f6ff;
    font-weight: normal;
    text-align: left;
    margin-top: 20px;
    font-family: 'Courier New', monospace;
}

</style>
""", unsafe_allow_html=True)

# # ---- Splash screen ----
# splash = st.empty()  # espace temporaire

# splash.markdown("""
# <style>
# @keyframes rotate {
#   from { transform: rotate(0deg) translateX(100px) rotate(0deg); }
#   to { transform: rotate(360deg) translateX(100px) rotate(-360deg); }
# }
# .emoji-orbit {
#   display: inline-block;
#   position: relative;
#   animation: rotate 4s linear infinite;
#   font-size: 30px;  /* <- Taille de l'emoji */
# }
# .center-container {
#   display:flex;
#   justify-content:center;
#   align-items:center;
#   height:100vh;
#   flex-direction:column;
#   position: relative;
# }
# </style>

# <div class="center-container">
#     <h1>Vlozy</h1>
#     <div class="emoji-orbit" style="position:absolute;">📄</div>
# </div>
# """, unsafe_allow_html=True)


# Simulation du temps de chargement (ex : récupération des données)
#time.sleep(3)  # ici tu peux mettre tes calculs ou chargement de données

# Supprimer le splash screen
#splash.empty()


# ---------- TITLE ----------
st.markdown(
    "<h1 style='text-align: center;'>🤖 Vlozy: Automate & Extract Data</h1>",
    unsafe_allow_html=True
)

# --- Function to load a JSON file (Lottie) ---
def load_lottiefile(filepath: str):
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)
    
# --- Function to process batch of files ---
def process_batch():
    if "batch_results" not in st.session_state:
            with st.spinner("Processing files... this may take some time."):
                all_results = []
                with open(zone_data_file, "r") as f:
                    zones_to_apply = json.load(f)
                for uploaded_batch_file in batch_files:
                    file_image = load_file_as_image(uploaded_batch_file)
                    extraction_dict = {}
                    for zone in zones_to_apply:
                        x1, y1 = zone["left"], zone["top"]
                        x2, y2 = x1 + zone["width"], y1 + zone["height"]
                        cropped_img = file_image.crop((x1, y1, x2, y2))
                        text_list = reader.readtext(
                            np.array(cropped_img.resize((cropped_img.width*3, cropped_img.height*3))),
                            detail=0
                        )
                        text_str = " ".join(text_list)
                        text_str = re.sub(r'(?<=\d) (?=\d{2}$)', '.', text_str)
                        extraction_dict[zone["name"]] = text_str
                    extraction_dict["file_name"] = uploaded_batch_file.name
                    all_results.append(extraction_dict)
                    time.sleep(1)
                st.session_state.batch_results = all_results
                st.success("🎉 Batch processing completed!")

        # Afficher le bouton de téléchargement uniquement si les résultats existent
    if st.session_state.batch_results:
        df_all = pd.DataFrame(st.session_state.batch_results)
        st.download_button(
            label="📥 Download results as CSV",
            data=df_all.to_csv(index=False).encode("utf-8"),
            file_name="batch_extract_results.csv",
            mime="text/csv"
        )

# --- Function to convert any file to image ---
def load_file_as_image(uploaded_file):
    """Charge n'importe quel fichier (pdf, txt, image) et renvoie un objet PIL.Image"""
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

        return file_image

    else:
        return Image.open(io.BytesIO(file_bytes))


# ---------- STEP 0: UPLOAD + ANIMATION ----------
col_upload, col_animation = st.columns([1,1])

with col_upload:
    st.markdown("### 1️⃣ Upload your file")
    txt_upload = "Upload your file here, which will be used to define the zones containing the information you want to extract."
    uploaded_file = st.file_uploader(txt_upload, type=["pdf", "txt"])
    st.caption("💬 At present, the application supports only single-page files.")

    # --- Checkbox to use existing zones JSON ---
    use_existing_zones = st.checkbox(
        "If you already have a JSON file with extraction zones, check this box to skip steps 2 and 3."
    )

    zones_from_file = None
    if use_existing_zones:
        uploaded_zones_file = st.file_uploader(
            "Upload your zones configuration JSON",
            type=["json"],
            key="zones_uploader"
        )
        if uploaded_zones_file:
            zones_from_file = json.load(uploaded_zones_file)
            st.success("✔️ Zones configuration loaded successfully! You can continue directly.")
            st.caption("The areas in this table will be used to extract and read data across all your files.")
            df_zones = pd.DataFrame(zones_from_file)
            st.dataframe(df_zones, use_container_width=True, hide_index=True)

            # ---------- STEP 4: BATCH EXTRACTION DIRECT ----------
            st.markdown("###  2️⃣ Batch of files")
            batch_files = st.file_uploader(
                "Upload multiple files", 
                type=["pdf", "txt"], accept_multiple_files=True,
                key="batch_direct"
            )

            if batch_files:
                process_batch()

with col_animation:
    lottie_animation = load_lottiefile("animation.json")
    st_lottie(lottie_animation, speed=1, loop=True, quality="high",width=500)


# ---------- SI PAS DE JSON : FLUX CLASSIQUE ----------
if uploaded_file and not zones_from_file:
    file_image = load_file_as_image(uploaded_file)
    st.success("✔️ File loaded and a preview is displayed.")

    # Cas 1 : zones définies manuellement
    st.markdown("### 2️⃣ Define the zones")
    col1, col2 = st.columns([1, 3])

    with col1:
        nb_zones = st.number_input("How many zones to define?", min_value=1, step=1)
        zone_names = []
        st.write("**Enter zone names (in order):**")
        for i in range(nb_zones):
            name = st.text_input(f"Zone {i+1} name", key=f"name_{i}")
            zone_names.append(name)

        if all(name.strip() != "" for name in zone_names) and nb_zones > 0:
            flash_placeholder = st.empty()
            flash_placeholder.markdown(
                '<div class="flash-box">⚡ After entering the zone names, you can now draw rectangles around the areas you want to extract in the image. Make sure to draw them in the same order as the zone names.<ul>' +
                ''.join([f"<li>{idx+1}. {nm}</li>" for idx, nm in enumerate(zone_names)]) + 
                "If a rectangle is incorrect and you want to redo it, you can use the tools below the image.</ul></div>",
                unsafe_allow_html=True
            )

    with col2:
        canvas_col, alert_col = st.columns([4,1])
        with canvas_col:
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

        with alert_col:
            if canvas_result.json_data and len(canvas_result.json_data["objects"]) == nb_zones:
                st.markdown(
                    '<div class="side-alert">✅ The number of rectangles you have drawn matches the number of zone names. You can now proceed to the next section to view the extraction results in a table.</div>',
                    unsafe_allow_html=True
                )

    # ---------- STEP 3: VALIDATE & OCR ----------
    st.markdown("### 3️⃣ Validate Data Extraction Quality")
    zones_to_apply = None

    if 'canvas_result' in locals() and canvas_result.json_data:
        objects = canvas_result.json_data["objects"]
        if len(objects) == nb_zones:
            zones_to_save = []
            extraction_dict = {}

            for obj, name in zip(objects, zone_names):
                x1, y1 = int(obj['left']), int(obj['top'])
                x2, y2 = x1 + int(obj['width']), y1 + int(obj['height'])
                cropped_img = file_image.crop((x1, y1, x2, y2))
                cropped = ImageOps.expand(cropped_img, border=10, fill="white")
                text_list = reader.readtext(np.array(cropped.resize((cropped.width*3, cropped.height*3))), detail=0)
                text_str = " ".join(text_list)
                text_str = re.sub(r'(?<=\d) (?=\d{2}$)', '.', text_str)
                zones_to_save.append({
                    "name": name,
                    "left": x1, "top": y1,
                    "width": int(obj['width']), "height": int(obj['height'])
                })
                extraction_dict[name] = [" ".join(text_str)]

            with open(zone_data_file, "w") as f:
                json.dump(zones_to_save, f)
            st.caption(" The table above displays the extracted zone names along with their corresponding values.")            
            df = pd.DataFrame(extraction_dict).reset_index(drop=True)
            st.dataframe(df.style.set_properties(**{'text-align': 'center'}), use_container_width=True, hide_index=True)
            st.caption("📌 If the results look good for you, save the zones to reuse them for similar templates.")
            zones_json = json.dumps(zones_to_save, indent=4)
            if st.download_button(
                label="📥 Download zones configuration (JSON)",
                data=zones_json, file_name="extraction_zones.json", mime="application/json"
            ):
                st.success("✔️ Zones successfully saved! Configuration stored.")

    # ---------- STEP 4: BATCH EXTRACTION ----------
    apply_batch = st.checkbox("By checking this box, you can perform a bulk extraction using the zones you have already created.")
    if apply_batch:
        st.info("You can now apply the same extraction zones to a larger batch of files.")
        st.markdown("### 4️⃣ Batch of files")
        batch_files = st.file_uploader(
            "Upload multiple files", 
            type=["pdf", "txt"], accept_multiple_files=True
        )

        if batch_files:
            process_batch()

