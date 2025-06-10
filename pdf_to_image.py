
import fitz  # PyMuPDF
import os

def convert_pdf_to_image(pdf_path, output_image_path=None, dpi=300, page_number=0):
    """
    Converts a specific page of a PDF to an image (PNG).

    Args:
        pdf_path (str): Path to the PDF file.
        output_image_path (str): Path to save the output PNG image. If None, will use pdf_path + "_page.png".
        dpi (int): Dots per inch (resolution).
        page_number (int): Page index to convert (0-based).

    Returns:
        str: Path to the saved PNG image.
    """
    doc = fitz.open(pdf_path)
    page = doc.load_page(page_number)
    mat = fitz.Matrix(dpi / 72, dpi / 72)  # scale matrix
    pix = page.get_pixmap(matrix=mat, alpha=False)

    if not output_image_path:
        output_image_path = pdf_path.replace(".pdf", f"_page{page_number}.png")

    pix.save(output_image_path)
    return output_image_path
