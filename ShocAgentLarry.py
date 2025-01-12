import streamlit as st
from PIL import Image, ImageFile, ImageDraw
import os
import io
import subprocess
from fpdf import FPDF

# --- Configure PIL to handle large images ---
Image.MAX_IMAGE_PIXELS = None
ImageFile.LOAD_TRUNCATED_IMAGES = True

# --- Streamlit Page Configuration ---
st.set_page_config(page_title="Print-Ready Validator")

# --- Utility Functions ---
def ensure_fpdf_installed():
    """Ensures fpdf library is installed."""
    try:
        from fpdf import FPDF
    except ImportError:
        subprocess.run([sys.executable, "-m", "pip", "install", "fpdf"], check=True)
        from fpdf import FPDF

def validate_print_readiness(img):
    """Validate if an image is print-ready."""
    dpi = img.info.get("dpi", (72, 72))  # Default DPI if not specified
    width_px, height_px = img.size
    width_mm = (width_px / dpi[0]) * 25.4
    height_mm = (height_px / dpi[1]) * 25.4
    color_mode = img.mode

    warnings = []
    if dpi[0] < 300 or dpi[1] < 300:
        warnings.append("Image DPI is below 300. Consider enhancing resolution.")
    if color_mode != "CMYK":
        warnings.append("Image is not in CMYK color mode. Convert for print readiness.")
    if width_mm < 210 or height_mm < 297:  # A4 size in mm
        warnings.append("Image dimensions are smaller than A4 size (210mm x 297mm).")

    return {
        "dpi": dpi,
        "dimensions_mm": (round(width_mm, 2), round(height_mm, 2)),
        "warnings": warnings
    }

def enhance_image(img):
    """Enhance image for print-readiness."""
    if img.mode != "CMYK":
        img = img.convert("CMYK")

    # Set DPI to 300
    img.info["dpi"] = (300, 300)
    return img

def add_bleed_marks(img, bleed_mm=5):
    """Adds 5mm bleed marks to the image."""
    dpi = img.info.get("dpi", (72, 72))
    bleed_px = int((bleed_mm * dpi[0]) / 25.4)  # Convert bleed from mm to pixels

    # Get original image size
    original_width, original_height = img.size

    # Create new canvas with bleed area
    new_width = original_width + 2 * bleed_px
    new_height = original_height + 2 * bleed_px
    new_img = Image.new(img.mode, (new_width, new_height), "white")  # White background for bleed

    # Paste the original image onto the new canvas
    new_img.paste(img, (bleed_px, bleed_px))

    # Draw bleed marks (optional visual guides)
    draw = ImageDraw.Draw(new_img)
    draw.rectangle(
        [bleed_px, bleed_px, bleed_px + original_width, bleed_px + original_height],
        outline="red",
        width=1,
    )  # Red rectangle to indicate the original image boundary

    return new_img

def create_pdf(file_details, output_filename="output.pdf"):
    """Creates a combined PDF with enhanced images."""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 10, "Appendix", ln=True, align="C")
    pdf.ln(10)

    for detail in file_details:
        pdf.cell(0, 10, f"{detail['index']}: {detail['name']} - {detail.get('type', 'Unknown')}", ln=True)

    for detail in file_details:
        if detail["type"] == "Image" and detail["enhanced_image"]:
            img = detail["enhanced_image"]
            img_path = f"temp_{detail['name']}"
            img.save(img_path, dpi=(300, 300))

            pdf.add_page()
            pdf.image(img_path, x=10, y=10, w=180)

            pdf.set_y(10 + (180 / img.width) * img.height + 10)
            pdf.set_font("Arial", size=10)
            pdf.cell(0, 10, f"File Name: {detail['name']}", ln=True, align="C")
            pdf.cell(0, 10, f"Dimensions (mm): {detail.get('dimensions_mm', 'Unknown')}", ln=True, align="C")
            pdf.cell(0, 10, f"Resolution (DPI): {detail.get('dpi', 'Unknown')}", ln=True, align="C")
            pdf.cell(0, 10, f"Color Mode: {detail.get('color_mode', 'Unknown')}", ln=True, align="C")
            if detail["warnings"]:
                pdf.set_text_color(255, 0, 0)
                for warning in detail["warnings"]:
                    pdf.cell(0, 10, f"Warning: {warning}", ln=True, align="C")
                pdf.set_text_color(0, 0, 0)

            os.remove(img_path)

    pdf.output(output_filename)
    return output_filename

# --- Streamlit UI ---
st.title("Print-Ready File Validator")

uploaded_files = st.file_uploader("Upload Files (Images and PDFs)", accept_multiple_files=True)

if uploaded_files:
    file_details = []
    for idx, file in enumerate(uploaded_files, start=1):
        info = {"name": file.name, "index": idx, "type": None, "dpi": None,
                "dimensions_mm": None, "warnings": [], "enhanced_image": None, "color_mode": None}

        if file.name.lower().endswith(('png', 'jpg', 'jpeg', 'tiff', 'bmp', 'gif')):
            try:
                img = Image.open(file)
                info["type"] = "Image"
                info["color_mode"] = img.mode  # Add color mode to the details

                # Validate print readiness
                validation = validate_print_readiness(img)
                info["dpi"] = validation["dpi"]
                info["dimensions_mm"] = validation["dimensions_mm"]
                info["warnings"].extend(validation["warnings"])

                # Add bleed marks if requested
                if st.checkbox(f"Add 5mm bleed to {file.name}?", key=f"bleed_{idx}"):
                    img_with_bleed = add_bleed_marks(img, bleed_mm=5)
                    info["enhanced_image"] = img_with_bleed
                else:
                    info["enhanced_image"] = img
            except Exception as e:
                st.error(f"Error processing {file.name}: {str(e)}")
        file_details.append(info)

    st.subheader("Uploaded File Details")
    for detail in file_details:
        st.write(f"{detail['index']}. {detail['name']} - {detail.get('type', 'Unknown')}")
        if detail["enhanced_image"]:
            st.image(detail["enhanced_image"], caption=f"Enhanced {detail['name']}", width=300)
        if detail["dpi"]:
            st.write(f"Resolution: {detail['dpi']} DPI")
        if detail["dimensions_mm"]:
            st.write(f"Dimensions: {detail['dimensions_mm']} mm (original)")
            bleed_dimensions = (
                detail["dimensions_mm"][0] + 10,  # Add 10mm (5mm on each side)
                detail["dimensions_mm"][1] + 10,
            )
            st.write(f"Dimensions with Bleed: {bleed_dimensions} mm")
        if detail["warnings"]:
            for warning in detail["warnings"]:
                st.error(warning)

    if st.button("Generate Combined PDF"):
        output_pdf = create_pdf(file_details)
        with open(output_pdf, "rb") as pdf_file:
            st.download_button("Download Combined PDF", data=pdf_file, file_name=output_pdf, mime="application/pdf")
else:
    st.info("Please upload files to begin.")
