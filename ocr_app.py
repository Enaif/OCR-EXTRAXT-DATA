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

