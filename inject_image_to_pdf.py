
import fitz  # PyMuPDF

def inject_image_into_pdf(original_pdf_path: str, image_path: str, output_pdf_path: str = None) -> str:
    """
    Replace the content of the first page in a PDF with an image (full page coverage).

    Args:
        original_pdf_path (str): Path to the original PDF to use dimensions.
        image_path (str): Path to the AI-filled image to inject.
        output_pdf_path (str): Optional path to save the modified PDF.

    Returns:
        str: Path to the output PDF.
    """
    doc = fitz.open(original_pdf_path)
    page = doc[0]
    rect = page.rect

    # Create a new blank page with same dimensions
    new_doc = fitz.open()
    new_page = new_doc.new_page(width=rect.width, height=rect.height)

    # Insert image to cover full page
    new_page.insert_image(rect, filename=image_path)

    # Save output
    if not output_pdf_path:
        output_pdf_path = original_pdf_path.replace(".pdf", "_final.pdf")
    new_doc.save(output_pdf_path, deflate=True)
    return output_pdf_path
