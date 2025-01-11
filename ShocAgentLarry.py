import streamlit as st
from PIL import Image, ImageFile
import os
import io
import subprocess

# --- Ensure `fpdf` is installed ---
def ensure_fpdf_installed():
    try:
        from fpdf import FPDF
    except ImportError:
        print("`fpdf` not found. Installing...")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "fpdf"],
            capture_output=True,
            text=True,
        )
        print("Installation output:", result.stdout)
        print("Installation errors:", result.stderr)
        from fpdf import FPDF

ensure_fpdf_installed()
from fpdf import FPDF

# --- Configure PIL to handle large images ---
Image.MAX_IMAGE_PIXELS = None  # Disable the safety limit for large images
ImageFile.LOAD_TRUNCATED_IMAGES = True  # Handle truncated image files gracefully

# --- Streamlit Page Configuration ---
st.set_page_config(page_title="Larry")  # Ensure this is the first Streamlit command

# --- Add Dark Mode Styling ---
st.markdown(
    """
    <style>
    body {
        background-color: #262730;
        color: #ffffff;
    }
    .stButton > button {
        background-color: #ff6347;
        color: white;
    }
    .stFileUploader label {
        color: #ffffff;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# --- Utility Functions ---
def play_warning_sound():
    """Play a warning sound using HTML."""
    sound_html = """
    <script>
    var audio = new Audio('https://www.soundjay.com/button/sounds/beep-01a.mp3');
    audio.play();
    </script>
    """
    st.markdown(sound_html, unsafe_allow_html=True)

# --- Agent 1: File Type Detection ---
def file_type_detection(uploaded_files):
    """Detects file types and gathers initial metadata."""
    details = []
    for file in uploaded_files:
        idx = len(details) + 1
        info = {"name": file.name, "index": idx, "type": None, "dimensions": None,
                "color_mode": None, "resolution": None, "image_object": None, "print_quality": None}

        if file.name.lower().endswith(('png', 'jpg', 'jpeg', 'tiff', 'bmp', 'gif')):
            try:
                img = Image.open(file)
                info["type"] = "Image"
                info["dimensions"] = img.size
                info["color_mode"] = img.mode
                dpi = img.info.get("dpi", None)
                if dpi:
                    info["resolution"] = (round(dpi[0], 1), round(dpi[1], 1))
                else:
                    info["resolution"] = "Not available"

                # Convert CMYK to RGB for thumbnails
                if img.mode == "CMYK":
                    img = img.convert("RGB")

                # Create a thumbnail for display
                thumbnail_size = (500, 500)
                img.thumbnail(thumbnail_size)
                img_bytes = io.BytesIO()
                img.save(img_bytes, format="PNG")
                img_bytes.seek(0)
                info["image_object"] = img_bytes
            except Exception as e:
                info["error"] = f"Error processing file: {str(e)}"

        elif file.name.lower().endswith("pdf"):
            info["type"] = "PDF"

        details.insert(0, info)
    return details

# --- Agent 2: Validation and Warnings ---
def validate_files(file_details):
    """Validates files for print readiness and adds warnings or success messages."""
    for idx, info in enumerate(file_details, start=1):
        info["index"] = idx
        if info["type"] == "Image":
            if info["color_mode"] == "RGB":
                info["warning"] = "Image is in RGB color mode. Consider converting to CMYK for print."
            elif info["color_mode"] == "RGBA":
                info["warning"] = "Image is in RGBA color mode."
                play_warning_sound()
            elif info["color_mode"] == "CMYK":
                info["success"] = "Image is in CMYK color mode, suitable for print."
    return file_details

# --- Agent 3: PDF Creation ---
def create_pdf(file_details, output_filename="output.pdf"):
    """Creates a combined PDF with an appendix and images."""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 10, "Appendix", ln=True, align="C")
    pdf.ln(10)

    for detail in file_details:
        pdf.cell(0, 10, f"{detail['index']}: {detail['name']} - {detail.get('type', 'Unknown')}", ln=True)

    for detail in file_details:
        if detail["type"] == "Image" and detail["image_object"]:
            img = Image.open(detail["image_object"])
            img_path = f"temp_{detail['name']}"
            img.save(img_path)

            pdf.add_page()
            pdf.image(img_path, x=10, y=10, w=180)

            pdf.set_y(10 + (180 / img.width) * img.height + 10)
            pdf.set_font("Arial", size=10)
            pdf.cell(0, 10, f"File Name: {detail['name']}", ln=True, align="C")
            pdf.cell(0, 10, f"Dimensions: {detail['dimensions']}", ln=True, align="C")
            pdf.cell(0, 10, f"Color Mode: {detail['color_mode']}", ln=True, align="C")
            if "warning" in detail:
                pdf.set_text_color(255, 0, 0)
                pdf.cell(0, 10, f"Warning: {detail['warning']}", ln=True, align="C")
                pdf.set_text_color(0, 0, 0)
            if "success" in detail:
                pdf.set_text_color(0, 128, 0)
                pdf.cell(0, 10, f"Success: {detail['success']}", ln=True, align="C")
                pdf.set_text_color(0, 0, 0)

            os.remove(img_path)

    pdf.output(output_filename)
    return output_filename

# --- Streamlit UI ---
st.title("File Analysis Tool")

uploaded_files = st.file_uploader("Upload Files (Images and PDFs)", accept_multiple_files=True)

if uploaded_files:
    file_details = file_type_detection(uploaded_files)
    file_details = validate_files(file_details)

    st.subheader("Uploaded File Details")
    for detail in file_details:
        st.write(f"{detail['index']}. {detail['name']} - {detail.get('type', 'Unknown')}")
        if detail["type"] == "Image" and detail["image_object"]:
            st.image(detail["image_object"], caption=f"Thumbnail of {detail['name']}", width=300)
        if "dimensions" in detail:
            st.write(f"Dimensions: {detail['dimensions']} pixels")
        if "color_mode" in detail:
            st.write(f"Color Mode: {detail['color_mode']}")
        if "resolution" in detail:
            st.write(f"Resolution: {detail['resolution']} DPI")
        if "warning" in detail:
            st.error(detail["warning"])
        if "success" in detail:
            st.success(detail["success"])

    if st.button("Generate Combined PDF"):
        output_pdf = create_pdf(file_details)
        with open(output_pdf, "rb") as pdf_file:
            st.download_button("Download Combined PDF", data=pdf_file, file_name=output_pdf, mime="application/pdf")
else:
    st.info("Please upload files to begin.")
