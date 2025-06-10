import fitz  # PyMuPDF
import os

def create_spot_color_definition():
    """Create a PDF spot color definition for CutContour"""
    # PDF operators for defining a spot color separation
    spot_color_def = """
    % Define CutContour spot color (Pure Magenta: C=0 M=100 Y=0 K=0)
    /CutContourCS [ /Separation /CutContour /DeviceCMYK
    <<
    /FunctionType 2
    /Domain [0 1]
    /Range [0 1 0 1 0 1 0 1]
    /C0 [0 0 0 0]  % CMYK values when tint = 0
    /C1 [0 1 0 0]  % CMYK values when tint = 1 (pure magenta)
    /N 1           % Linear interpolation
    >>
    ] def
    
    % Register color space in the current graphics state
    /CutContourCS setcolorspace
    """
    return spot_color_def.strip()

def add_spot_color_resources(page):
    """Add spot color resources to the page"""
    # Get existing resources dictionary or create new one
    resources = page.get_contents()
    if not resources:
        resources = {}

    # Add ColorSpace definition if not present
    if "ColorSpace" not in resources:
        resources["ColorSpace"] = {}
    
    # Add our spot color definition
    resources["ColorSpace"]["CutContourCS"] = create_spot_color_definition()
    
    # Update page resources
    page.set_contents(resources)

def add_spot_color_layer(pdf_path, shape, bleed_mm, width_mm, height_mm, dpi):
    doc = fitz.open(pdf_path)
    trim_x = bleed_mm * dpi / 25.4
    trim_y = bleed_mm * dpi / 25.4
    trim_width = width_mm * dpi / 25.4
    trim_height = height_mm * dpi / 25.4

    # Define spot color for CutContour
    cut_color = (1, 0, 1)  # Magenta
    spot_color = {"name": "CutContour", "space": "Separation", "c": cut_color}

    for page in doc:
        if shape == "circle":
            rect = fitz.Rect(trim_x, trim_y, trim_x + trim_width, trim_y + trim_height)
            shape_obj = page.new_shape()
            shape_obj.draw_oval(rect)
            shape_obj.finish(color=None, width=0.25, fill=None, stroke_color=spot_color)
            shape_obj.commit()
        else:
            rect = fitz.Rect(trim_x, trim_y, trim_x + trim_width, trim_y + trim_height)
            shape_obj = page.new_shape()
            shape_obj.draw_rect(rect)
            shape_obj.finish(color=None, width=0.25, fill=None, stroke_color=spot_color)
            shape_obj.commit()
    output_path = pdf_path.replace(".pdf", "_final.pdf")
    doc.save(output_path, deflate=True)
    return output_path
