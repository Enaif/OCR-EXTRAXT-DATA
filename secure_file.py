import streamlit as st
from pypdf import PdfReader, PdfWriter, constants
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.colors import HexColor
import io
import base64
import gc  # Garbage collector pour libérer la mémoire

st.set_page_config(page_title="🔐 FileProtector", layout="wide")

# --- Background ---
def get_base64_of_bin_file(bin_file):
    with open(bin_file, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()

bin_str = get_base64_of_bin_file("pexels-pavel-danilyuk-8294552.jpg")
page_bg = f"""
<style>
[data-testid="stAppViewContainer"] {{
    background-image: url("data:image/jpg;base64,{bin_str}");
    background-size: cover;
    background-position: center;
    background-repeat: no-repeat;
}}
[data-testid="stHeader"] {{
    background: rgba(0,0,0,0);
}}
[data-testid="stToolbar"] {{
    right: 2rem;
}}
</style>
"""
st.markdown(page_bg, unsafe_allow_html=True)

# --- Title + Upload ---
with st.container(): 
    col1, col2, col3 = st.columns(3) 
    with col1: 
        pass 
    with col2: 
        st.markdown("""
        <h1 style="
            text-align: center; 
            color: white; 
            font-family: 'Courier New', Courier, monospace; 
            text-shadow: 2px 2px 5px white;
            font-size: 40px;">
            FILE PROTECTOR
        </h1>
        """, unsafe_allow_html=True)
        uploaded_file = st.file_uploader("PDF Upload", type="pdf", label_visibility="collapsed")
    with col3: 
        pass

if uploaded_file:
    # --- Tabs for options ---
    tab1, tab2, tab3 = st.tabs(["🖊️ Watermark", "🔑 Password", "🚫 Restrictions"])
    
    # === Watermark ===
    with tab1:
        add_watermark = st.checkbox("Enable watermark to authenticate your document")
        watermark_text, watermark_color, watermark_size, watermark_angle, watermark_alpha, apply_pages = "", "", 0, 0, 0, ""
        if add_watermark:
            watermark_text = st.text_input("Watermark Text", value="CONFIDENTIAL")
            watermark_color = st.color_picker("Watermark Color", "#00fff0")
            watermark_size = st.slider("Text Size", 20, 100, 40)
            watermark_angle = st.slider("Rotation Angle", 0, 360, 45)
            watermark_alpha = st.slider("Transparency", 0.1, 1.0, 0.3)
            apply_pages = st.text_input("Pages (e.g., 1-3 or leave empty = all)", value="")
    
    # === Password ===
    with tab2:
        add_password = st.checkbox("Enable password protection")
        password = ""
        if add_password:
            password = st.text_input("PDF Password", type="password")
    
    # === Restriction ===
    with tab3:
        restrict_copy = st.checkbox("Disable copy to protect the content of your document")
    
    # === Main Button ===
    if st.button("🔒 Secure PDF", use_container_width=True):
        try:
            # --- Lecture PDF uniquement en mémoire ---
            reader = PdfReader(uploaded_file)
            writer = PdfWriter()

            # --- Créer watermark ---
            def create_watermark(text, color, size, angle, alpha):
                packet = io.BytesIO()
                can = canvas.Canvas(packet, pagesize=letter)
                can.setFont("Helvetica-Bold", size)
                can.setFillColor(HexColor(color))
                can.setFillAlpha(alpha)
                can.saveState()
                can.translate(300, 400)
                can.rotate(angle)
                can.drawCentredString(0, 0, text)
                can.restoreState()
                can.save()
                packet.seek(0)
                return PdfReader(packet)

            if add_watermark:
                watermark = create_watermark(watermark_text, watermark_color, watermark_size, watermark_angle, watermark_alpha)
                total_pages = len(reader.pages)
                if apply_pages.strip():
                    pages_to_apply = []
                    for part in apply_pages.split(","):
                        if "-" in part:
                            start, end = map(int, part.split("-"))
                            pages_to_apply.extend(range(start-1, end))
                        else:
                            pages_to_apply.append(int(part)-1)
                else:
                    pages_to_apply = list(range(total_pages))
            else:
                pages_to_apply = []

            # --- Appliquer watermark et pages ---
            for i, page in enumerate(reader.pages):
                if add_watermark and i in pages_to_apply:
                    page.merge_page(watermark.pages[0])
                writer.add_page(page)

            #--- Protection PDF ---
            if add_password or restrict_copy:
                if add_password and not password:
                    st.error("⚠️ You must enter a password.")
                    st.stop()
                permissions = 0
                if not restrict_copy:
                    permissions |= constants.UserAccessPermissions.PRINT
                    permissions |= constants.UserAccessPermissions.MODIFY
                    permissions |= constants.UserAccessPermissions.EXTRACT_TEXT_AND_GRAPHICS
                writer.encrypt(
                    user_password=password if password else "",
                    owner_password=password if password else None,
                    use_128bit=True,
                    permissions_flag=permissions
                 )
            # --- Protection PDF ---

            output_buffer = io.BytesIO()
            writer.write(output_buffer)
            output_buffer.seek(0)

            st.success("✅ PDF successfully secured!")
            st.download_button(
                "📥 Download Secured PDF",
                data=output_buffer,
                file_name="secured_document.pdf",
                mime="application/pdf",
                use_container_width=True
            )

            # --- Nettoyage complet ---
            del reader, writer, watermark, output_buffer
            gc.collect()  # Force libération mémoire

        except Exception as e:
            st.error(f"❌ Error: {e}")
else:
    with col2: 
        st.info("⬆️ Upload a PDF file to get started.")

# --- Message rassurant pour l'utilisateur ---
st.markdown("""
<div style="
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    width: 100%;
    text-align: center;
    color: white;
    text-decoration: none;
    font-family: monospace;
    background: rgba(0,0,0,0.3);  /* couvre toute la largeur */
    padding: 0.5rem 0;
    z-index: 9999;
    box-sizing: border-box;">
    All files are processed entirely in memory, leaving no trace on the server to ensure security.
</div>
""", unsafe_allow_html=True)


