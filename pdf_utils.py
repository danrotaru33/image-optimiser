import fitz  # PyMuPDF
import os
from pydantic import BaseModel
import requests

def analyze_pdf(input_path):
    doc = fitz.open(input_path)
    page = doc[0]
    width_pt, height_pt = page.rect.width, page.rect.height
    dpi = 300  # Default
    # Try to get DPI from metadata (PyMuPDF doesn't always provide this)
    try:
        meta = doc.metadata
        if meta and 'dpi' in meta and meta['dpi']:
            dpi = int(meta['dpi'])
    except Exception:
        pass
    width_mm = width_pt * 25.4 / 72
    height_mm = height_pt * 25.4 / 72
    orientation = "landscape" if width_mm > height_mm else "portrait"
    return {
        "width_mm": width_mm,
        "height_mm": height_mm,
        "width_px": int(width_pt / 72 * dpi),
        "height_px": int(height_pt / 72 * dpi),
        "orientation": orientation,
        "dpi": dpi,
        "page_count": len(doc)
    }

def resize_pdf_with_bleed(input_path, width_mm, height_mm, bleed_mm, dpi):
    # Final canvas includes bleed
    canvas_width_mm = width_mm + 2 * bleed_mm
    canvas_height_mm = height_mm + 2 * bleed_mm
    canvas_width_px = int(canvas_width_mm / 25.4 * dpi)
    canvas_height_px = int(canvas_height_mm / 25.4 * dpi)
    trim_width_px = int(width_mm / 25.4 * dpi)
    trim_height_px = int(height_mm / 25.4 * dpi)

    doc = fitz.open(input_path)
    new_doc = fitz.open()

    for page in doc:
        orig_width_px = int(page.rect.width / 72 * dpi)
        orig_height_px = int(page.rect.height / 72 * dpi)
        orig_aspect = orig_width_px / orig_height_px
        trim_aspect = trim_width_px / trim_height_px

        # Scale to fill trim area (no white lines)
        if orig_aspect > trim_aspect:
            scale = trim_height_px / orig_height_px
            scaled_width = int(orig_width_px * scale)
            scaled_height = trim_height_px
        else:
            scale = trim_width_px / orig_width_px
            scaled_width = trim_width_px
            scaled_height = int(orig_height_px * scale)

        # Center in trim area
        x_offset = (trim_width_px - scaled_width) // 2
        y_offset = (trim_height_px - scaled_height) // 2

        # Place trim area in the center of the bleed canvas
        trim_x = int(bleed_mm / 25.4 * dpi)
        trim_y = int(bleed_mm / 25.4 * dpi)

        new_page = new_doc.new_page(width=canvas_width_px, height=canvas_height_px)
        new_page.draw_rect(new_page.rect, color=(1, 1, 1), fill=(1, 1, 1))
        pix = page.get_pixmap(dpi=dpi)
        new_page.insert_image(
            fitz.Rect(trim_x + x_offset, trim_y + y_offset, trim_x + x_offset + scaled_width, trim_y + y_offset + scaled_height),
            pixmap=pix
        )

    output_path = input_path.replace(".pdf", "_resized.pdf")
    new_doc.save(output_path, deflate=True)
    return output_path

def create_test_pdf(filename, width_mm=210, height_mm=297):  # A4 size by default
    """Create a test PDF with a rectangle and text to test resizing"""
    doc = fitz.open()
    page = doc.new_page(width=float(width_mm * 72/25.4), height=float(height_mm * 72/25.4))
    
    # Draw a colored rectangle with some margin
    margin = 20
    rect = fitz.Rect(margin, margin, page.rect.width - margin, page.rect.height - margin)
    page.draw_rect(rect, color=(1, 0, 0))  # Red rectangle
    
    # Add some text
    font_size = 24
    text = "Test PDF Content"
    tw = fitz.get_text_length(text, fontname="helv", fontsize=font_size)
    text_point = fitz.Point((page.rect.width - tw) / 2, page.rect.height / 2)
    page.insert_text(text_point, text, fontname="helv", fontsize=font_size)
    
    doc.save(filename)
    doc.close()
    return filename

def detect_empty_zones(pdf_path, width_px, height_px, threshold=0.1):
    # For each page, detect if >10% of any edge is white (simple heuristic)
    # Returns a dict: {page_num: {"top": True, "bottom": False, ...}}
    doc = fitz.open(pdf_path)
    results = {}
    for i, page in enumerate(doc):
        pix = page.get_pixmap()
        img = pix.samples
        # For simplicity, just check the first/last N rows/columns for white
        # (A real implementation would use OpenCV or PIL for more accuracy)
        N = int(0.1 * min(width_px, height_px))
        white = 255
        # Check top
        top_white = all(b > 240 for b in img[:N*pix.width])
        # Check bottom
        bottom_white = all(b > 240 for b in img[-N*pix.width:])
        # Check left
        left_white = all(b > 240 for b in img[::pix.width][:N])
        # Check right
        right_white = all(b > 240 for b in img[pix.width-1::pix.width][:N])
        results[i] = {
            "top": top_white,
            "bottom": bottom_white,
            "left": left_white,
            "right": right_white
        }
    return results

def detect_and_mark_zones(pdf_path, empty_zones):
    # For each page, return bounding boxes for white areas (dummy: just return full edge if marked)
    doc = fitz.open(pdf_path)
    bboxes = {}
    for i, page in enumerate(doc):
        bboxes[i] = []
        for edge, is_empty in empty_zones[i].items():
            if is_empty:
                if edge == "top":
                    bboxes[i].append((0, 0, page.rect.width, page.rect.height * 0.1))
                elif edge == "bottom":
                    bboxes[i].append((0, page.rect.height * 0.9, page.rect.width, page.rect.height))
                elif edge == "left":
                    bboxes[i].append((0, 0, page.rect.width * 0.1, page.rect.height))
                elif edge == "right":
                    bboxes[i].append((page.rect.width * 0.9, 0, page.rect.width, page.rect.height))
    return bboxes

def ai_fill_zones(pdf_path, bboxes, dpi=300):
    # For each bbox, convert to image, send to Hugging Face, replace in PDF
    # This is a stub: in production, you'd use PIL/OpenCV and the Hugging Face API
    # Here, just fill with white if AI fails
    doc = fitz.open(pdf_path)
    for i, page in enumerate(doc):
        for bbox in bboxes.get(i, []):
            rect = fitz.Rect(*bbox)
            page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1))
    output_path = pdf_path.replace(".pdf", "_aifilled.pdf")
    doc.save(output_path, deflate=True)
    return output_path

def add_spot_color_layer(pdf_path, shape, bleed_mm):
    doc = fitz.open(pdf_path)
    for page in doc:
        bleed_pt = bleed_mm * 72 / 25.4
        if shape == "circle":
            # Draw ellipse inset by bleed
            rect = fitz.Rect(
                bleed_pt, bleed_pt,
                page.rect.width - bleed_pt, page.rect.height - bleed_pt
            )
            shape_obj = page.new_shape()
            shape_obj.draw_oval(rect)
            shape_obj.finish(color=(1, 0, 1), width=0.25, fill=None)
            shape_obj.commit()
        else:
            # Draw rectangle inset by bleed
            rect = fitz.Rect(
                bleed_pt, bleed_pt,
                page.rect.width - bleed_pt, page.rect.height - bleed_pt
            )
            shape_obj = page.new_shape()
            shape_obj.draw_rect(rect)
            shape_obj.finish(color=(1, 0, 1), width=0.25, fill=None)
            shape_obj.commit()
    output_path = pdf_path.replace(".pdf", "_cutline.pdf")
    doc.save(output_path, deflate=True)
    return output_path

class PDFAnalysis(BaseModel):
    width_mm: float
    height_mm: float
    width_px: int
    height_px: int
    orientation: str
    dpi: int
    page_count: int

class ProcessRequest(BaseModel):
    file_id: str
    width_mm: float
    height_mm: float
    bleed_mm: float
    dpi: int
    shape: str  # 'rectangle' or 'circle'
    spot_color: bool
    ai_fill: bool
