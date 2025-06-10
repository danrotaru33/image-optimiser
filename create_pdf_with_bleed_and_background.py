import fitz  # PyMuPDF
from PIL import Image
import io
import os

def create_pdf_with_bleed_and_background(original_pdf_path, filled_image_path, output_pdf_path, bleed_mm=3, dpi=300):
    """
    Creates a new PDF with:
    - AI-filled margin (raster background)
    - Original vector PDF content centered
    - Optional bleed around edges

    Args:
        original_pdf_path (str): Path to the original PDF file.
        filled_image_path (str): AI-filled background image (should include bleed).
        output_pdf_path (str): Path to save the final composited PDF.
        bleed_mm (float): Bleed margin in millimeters.
        dpi (int): Resolution used for conversion (used to calculate pixels from mm).
    """
    bleed_px = int(bleed_mm / 25.4 * dpi)

    # File type check before opening with PIL
    if not (filled_image_path.lower().endswith('.png') or filled_image_path.lower().endswith('.jpg')):
        raise ValueError("Only .png or .jpg images can be opened with PIL. Got: " + filled_image_path)

    # Load background image
    bg_img = Image.open(filled_image_path)
    bg_width_px, bg_height_px = bg_img.size

    # Convert px to mm
    bg_width_mm = bg_width_px / dpi * 25.4
    bg_height_mm = bg_height_px / dpi * 25.4

    # Open original PDF
    original_pdf = fitz.open(original_pdf_path)
    original_page = original_pdf.load_page(0)
    orig_rect = original_page.rect
    orig_width_mm = orig_rect.width * 25.4 / 72
    orig_height_mm = orig_rect.height * 25.4 / 72

    # Create new PDF with increased size
    new_pdf = fitz.open()
    page = new_pdf.new_page(width=bg_width_mm * 72 / 25.4, height=bg_height_mm * 72 / 25.4)

    # Insert raster background image (AI fill)
    bg_img_bytes = io.BytesIO()
    bg_img.save(bg_img_bytes, format="PNG")
    bg_img_bytes = bg_img_bytes.getvalue()
    page.insert_image(page.rect, stream=bg_img_bytes)

    # Insert original PDF content on top, offset to center (respect bleed)
    bleed_pts = bleed_mm * 72 / 25.4
    page.show_pdf_page(fitz.Rect(bleed_pts, bleed_pts, bleed_pts + orig_rect.width, bleed_pts + orig_rect.height),
                       original_pdf, 0)

    new_pdf.save(output_pdf_path)
    return output_pdf_path
