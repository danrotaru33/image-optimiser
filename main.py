import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/..'))

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uuid
import fitz
from PyPDF2 import PdfReader, PdfWriter
import json
from datetime import datetime
from PIL import Image

from app.pdf_utils import resize_pdf_with_bleed, analyze_pdf, detect_empty_zones
from app.ai_fill import ai_fill_margins
from app.spot_color import add_spot_color_layer
from app.inject_image_to_pdf import inject_image_into_pdf
from app.create_pdf_with_bleed_and_background import create_pdf_with_bleed_and_background
from app.extract_margin_strips import extract_margin_strips


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "static/uploads"
PROCESSED_DIR = "static/processed"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)

@app.post("/upload/")
async def upload_pdf(
    file: UploadFile = File(...),
    width_mm: str = Form(...),
    height_mm: str = Form(...),
    dpi: str = Form(...),
    bleed_mm: str = Form(...),
    add_spot_color: bool = Form(False),
    shape: str = Form("rectangle")
):
    try:
        # Convert form values to proper types
        width = float(width_mm)
        height = float(height_mm)
        dpi_value = int(dpi)
        bleed = float(bleed_mm)

        # Save uploaded file
        file_id = str(uuid.uuid4())
        input_path = os.path.join(UPLOAD_DIR, f"{file_id}.pdf")
        output_path = os.path.join(PROCESSED_DIR, f"{file_id}_processed.pdf")

        with open(input_path, "wb") as f:
            f.write(await file.read())

        # Step 1: Resize and add bleed
        resized_path = resize_pdf_with_bleed(input_path, width, height, bleed, dpi_value)

        # Step 2: AI fill margins and get image
        width_px = int((width) / 25.4 * dpi_value)
        height_px = int((height) / 25.4 * dpi_value)
        filled_image_path = ai_fill_margins(resized_path, width_px, height_px)

        # Step 3: Hybrid compositing of vector PDF and AI background
        final_pdf_path = create_pdf_with_bleed_and_background(
            original_pdf_path=resized_path,
            filled_image_path=filled_image_path,
            output_pdf_path=os.path.join(PROCESSED_DIR, f"{file_id}_processed.pdf"),
            bleed_mm=bleed,
            dpi=dpi_value
        )

        # Step 4: Add spot color (optional)
        if add_spot_color:
            final_path = add_spot_color_layer(final_pdf_path, shape, bleed, width, height, dpi_value)
            os.rename(final_path, output_path)
        else:
            final_path = final_pdf_path

        # Generate processing report
        report_dir = os.path.join("static", "reports")
        os.makedirs(report_dir, exist_ok=True)
        report_path = os.path.join(report_dir, f"{file_id}_report.json")
        empty_zones = detect_empty_zones(resized_path, int(width / 25.4 * dpi_value), int(height / 25.4 * dpi_value))
        report = {
            "file_id": file_id,
            "input_pdf": input_path,
            "output_pdf": output_path,
            "width_mm": width,
            "height_mm": height,
            "bleed_mm": bleed,
            "dpi": dpi_value,
            "empty_margins": empty_zones.get(0, {}),
            "ai_fill": True,
            "spot_color": add_spot_color,
            "hybrid_layering": True,
            "timestamp": datetime.now().isoformat()
        }
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)

        return JSONResponse(content={"status": "success", "file_path": output_path, "report": report_path, "hybrid_layering": True})

    except ValueError as e:
        return JSONResponse(
            content={
                "status": "error",
                "detail": f"Invalid input values: {str(e)}"
            },
            status_code=400
        )
    except Exception as e:
        return JSONResponse(
            content={
                "status": "error",
                "detail": str(e)
            },
            status_code=500
        )

@app.get("/download/")
def download_file(file_path: str):
    return FileResponse(path=file_path, filename=os.path.basename(file_path), media_type="application/pdf")

@app.post("/analyze/")
async def analyze_pdf_route(file: UploadFile = File(...)):
    # Save uploaded file temporarily
    file_id = str(uuid.uuid4())
    temp_path = os.path.join("static/uploads", f"{file_id}.pdf")

    with open(temp_path, "wb") as f:
        f.write(await file.read())

    # Analyze the PDF
    metadata = analyze_pdf(temp_path)
    empty_zones = detect_empty_zones(temp_path, metadata["width_px"], metadata["height_px"])

    return {
        "width_mm": metadata["width_mm"],
        "height_mm": metadata["height_mm"],
        "width_px": metadata["width_px"],
        "height_px": metadata["height_px"],
        "orientation": metadata["orientation"],
        "dpi": metadata["dpi"],
        "page_count": metadata["page_count"],
        "empty_margins": empty_zones.get(0, {})  # Just first page
    }

@app.post("/preview/")
async def preview_pdf(file: UploadFile = File(...)):
    file_id = str(uuid.uuid4())
    upload_dir = "static/uploads"
    preview_dir = "static/previews"
    os.makedirs(preview_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, f"{file_id}.pdf")
    output_path = os.path.join(preview_dir, f"{file_id}_preview.png")

    with open(file_path, "wb") as f_out:
        f_out.write(await file.read())

    doc = fitz.open(file_path)
    page = doc[0]
    pix = page.get_pixmap(dpi=150)
    pix.save(output_path)

    return {"status": "success", "preview_url": f"/static/previews/{file_id}_preview.png"}

def resize_pdf_with_bleed(input_path, width_mm, height_mm, bleed_mm, dpi):
    doc = fitz.open(input_path)
    new_doc = fitz.open()

    # Calculate final canvas size in points (1 pt = 1/72 inch)
    canvas_width_pt = (width_mm + 2 * bleed_mm) / 25.4 * 72
    canvas_height_pt = (height_mm + 2 * bleed_mm) / 25.4 * 72

    for page in doc:
        # Original page size in points
        orig_rect = page.rect
        orig_width_pt = orig_rect.width
        orig_height_pt = orig_rect.height

        # Calculate trim box (where the original page should be centered)
        trim_width_pt = width_mm / 25.4 * 72
        trim_height_pt = height_mm / 25.4 * 72
        trim_x = (canvas_width_pt - trim_width_pt) / 2
        trim_y = (canvas_height_pt - trim_height_pt) / 2

        # Center the original page in the new canvas
        x_offset = trim_x + (trim_width_pt - orig_width_pt) / 2
        y_offset = trim_y + (trim_height_pt - orig_height_pt) / 2

        new_page = new_doc.new_page(width=canvas_width_pt, height=canvas_height_pt)
        # Fill background with white
        new_page.draw_rect(new_page.rect, color=(1, 1, 1), fill=(1, 1, 1))

        # Try to use show_pdf_page for vector-perfect placement
        try:
            new_page.show_pdf_page(
                fitz.Rect(x_offset, y_offset, x_offset + orig_width_pt, y_offset + orig_height_pt),
                doc, page.number
            )
        except Exception:
            # Fallback: rasterize (not recommended, but ensures no crash)
            pix = page.get_pixmap(dpi=dpi)
            new_page.insert_image(
                fitz.Rect(x_offset, y_offset, x_offset + orig_width_pt, y_offset + orig_height_pt),
                pixmap=pix
            )

    output_path = input_path.replace(".pdf", "_resized.pdf")
    new_doc.save(output_path, deflate=True)
    return output_path

def add_spot_color_layer(pdf_path, shape, bleed_mm, width_mm, height_mm, dpi):
    doc = fitz.open(pdf_path)
    trim_x = bleed_mm * dpi / 25.4
    trim_y = bleed_mm * dpi / 25.4
    trim_width = width_mm * dpi / 25.4
    trim_height = height_mm * dpi / 25.4

    for page in doc:
        if shape == "circle":
            rect = fitz.Rect(trim_x, trim_y, trim_x + trim_width, trim_y + trim_height)
            shape_obj = page.new_shape()
            shape_obj.draw_oval(rect)
            shape_obj.finish(color=(1, 0, 1), width=0.25, fill=None)
            shape_obj.commit()
        else:
            rect = fitz.Rect(trim_x, trim_y, trim_x + trim_width, trim_y + trim_height)
            shape_obj = page.new_shape()
            shape_obj.draw_rect(rect)
            shape_obj.finish(color=(1, 0, 1), width=0.25, fill=None)
            shape_obj.commit()
    output_path = pdf_path.replace(".pdf", "_cutline.pdf")
    doc.save(output_path, deflate=True)
    return output_path

def convert_magenta_to_spot(input_pdf, output_pdf):
    reader = PdfReader(input_pdf)
    writer = PdfWriter()

    for page in reader.pages:
        # This is a simplified example. For production, you need to:
        # 1. Add a /Separation color space to the page's /Resources.
        # 2. Replace the magenta stroke operator with /CutContourCS CS and 1 SCN.
        # 3. Add the /CutContourCS definition to the PDF.
        # This is best done with a PDF library that allows low-level editing.
        writer.add_page(page)

    # Add spot color definition to the PDF catalog (advanced, see PDF spec)
    # For now, this script just copies the file. Use Enfocus PitStop or a prepress tool for production.

    with open(output_pdf, "wb") as f:
        writer.write(f)

def pdf_ai_margin_fill_pipeline(
    input_pdf_path,
    width_mm,
    height_mm,
    bleed_mm,
    dpi,
    shape="rectangle",
    output_dir="static/processed/"
):
    # Step 1: Resize PDF to final canvas with bleed
    resized_pdf = resize_pdf_with_bleed(input_pdf_path, width_mm, height_mm, bleed_mm, dpi)
    metadata = analyze_pdf(resized_pdf)
    width_px = int((width_mm + 2 * bleed_mm) / 25.4 * dpi)
    height_px = int((height_mm + 2 * bleed_mm) / 25.4 * dpi)

    # Step 2: Extract margin strips as PNGs
    strips = extract_margin_strips(resized_pdf, width_px, height_px, bleed_mm, dpi)
    # strips: dict with keys 'top', 'bottom', 'left', 'right' and PNG file paths

    # Step 3: AI fill each margin
    filled_strips = {}
    for side, strip_path in strips.items():
        filled_strips[side] = ai_fill_margins(strip_path, width=width_px, height=height_px)  # or use strip size

    # Step 4: Recombine filled strips into a background image
    # (Assume you have a function to do this, or implement below)
    bg = Image.new("RGB", (width_px, height_px), (255, 255, 255))
    for side, filled_path in filled_strips.items():
        strip_img = Image.open(filled_path)
        if side == "top":
            bg.paste(strip_img, (0, 0))
        elif side == "bottom":
            bg.paste(strip_img, (0, height_px - strip_img.height))
        elif side == "left":
            bg.paste(strip_img, (0, 0))
        elif side == "right":
            bg.paste(strip_img, (width_px - strip_img.width, 0))
    bg_path = os.path.join(output_dir, "ai_margin_bg.png")
    bg.save(bg_path)

    # Step 5: Composite background + vector PDF
    composited_pdf = os.path.join(output_dir, "composited.pdf")
    create_pdf_with_bleed_and_background(
        original_pdf_path=resized_pdf,
        filled_image_path=bg_path,
        output_pdf_path=composited_pdf,
        bleed_mm=bleed_mm,
        dpi=dpi
    )

    # Step 6: Add spot color cut line
    final_pdf = add_spot_color_layer(
        pdf_path=composited_pdf,
        shape=shape,
        bleed_mm=bleed_mm,
        width_mm=width_mm,
        height_mm=height_mm,
        dpi=dpi
    )

    # Step 7: Save result
    final_path = os.path.join(output_dir, "final_print_ready.pdf")
    os.rename(final_pdf, final_path)
    return final_path

if __name__ == "__main__":
    result_path = pdf_ai_margin_fill_pipeline(
        input_pdf_path="static/uploads/test_input_vector.pdf",
        width_mm=216,
        height_mm=303,
        bleed_mm=3,
        dpi=300,
        shape="rectangle",
        output_dir="static/processed/"
    )
    print(f"Pipeline complete. Output: {result_path}")
