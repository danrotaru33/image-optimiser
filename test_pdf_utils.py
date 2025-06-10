import fitz
import os
from pdf_utils import resize_pdf_with_bleed

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

def test_resize_scenarios():
    # Create test directory if it doesn't exist
    test_dir = "static/test"
    os.makedirs(test_dir, exist_ok=True)
    
    # Create test PDF (A4 portrait)
    test_pdf = os.path.join(test_dir, "test_original.pdf")
    create_test_pdf(test_pdf, width_mm=210, height_mm=297)  # A4
    
    # Test scenarios
    scenarios = [
        # Target size (width_mm, height_mm, bleed_mm, description, output_name)
        (210, 297, 3, "A4 with 3mm bleed", "a4_portrait"),
        (297, 210, 3, "A4 landscape with 3mm bleed", "a4_landscape"),
        (148, 210, 3, "A5 with 3mm bleed", "a5"),
        (420, 594, 3, "A2 with 3mm bleed", "a2"),
        (200, 200, 3, "Square format with 3mm bleed", "square"),
    ]
    
    results = []
    for width_mm, height_mm, bleed_mm, desc, output_name in scenarios:
        print(f"\nTesting: {desc}")
        print(f"Target dimensions: {width_mm}mm x {height_mm}mm with {bleed_mm}mm bleed")
        
        # Temporarily modify the input file to create a unique output name
        temp_input = test_pdf.replace(".pdf", f"_{output_name}_input.pdf")
        os.rename(test_pdf, temp_input)
        
        output_path = resize_pdf_with_bleed(temp_input, width_mm, height_mm, bleed_mm, dpi=300)
        final_output = output_path.replace("_input_resized.pdf", "_output.pdf")
        os.rename(output_path, final_output)
        
        # Restore original input name for next iteration
        os.rename(temp_input, test_pdf)
        
        print(f"Created: {final_output}")
        results.append(final_output)
    
    print("\nAll test files generated:")
    for path in results:
        print(f"- {path}")

if __name__ == "__main__":
    test_resize_scenarios() 