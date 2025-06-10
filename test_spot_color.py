import fitz
import os
from pdf_utils import create_test_pdf
from spot_color import add_spot_color_layer

def test_spot_color_cutlines():
    # Create test directory if it doesn't exist
    test_dir = "static/test_cutlines"
    os.makedirs(test_dir, exist_ok=True)
    
    # Test scenarios with different page sizes and bleed values
    scenarios = [
        # (width_mm, height_mm, bleed_mm, description)
        (210, 297, 3, "A4 portrait with 3mm bleed"),
        (297, 210, 3, "A4 landscape with 3mm bleed"),
        (148, 210, 5, "A5 with 5mm bleed"),  # Testing larger bleed
        (100, 100, 2, "Square with 2mm bleed"),  # Testing smaller bleed
        (50, 90, 3, "Business card with 3mm bleed")  # Small format test
    ]
    
    results = []
    for width_mm, height_mm, bleed_mm, desc in scenarios:
        print(f"\nTesting: {desc}")
        print(f"Dimensions: {width_mm}mm x {height_mm}mm, Bleed: {bleed_mm}mm")
        
        # Create a test PDF with some content
        test_name = desc.lower().replace(" ", "_")
        input_pdf = os.path.join(test_dir, f"{test_name}_input.pdf")
        
        # Create test PDF with colored rectangle and text
        create_test_pdf(input_pdf, width_mm=width_mm, height_mm=height_mm)
        
        # Add spot color cut line
        output_pdf = add_spot_color_layer(input_pdf, bleed_mm=bleed_mm)
        print(f"Created: {output_pdf}")
        results.append((desc, output_pdf))
    
    # Print summary
    print("\nTest files generated:")
    for desc, path in results:
        print(f"- {desc}: {path}")
        print("  Verify that:")
        print("  * Cut line is exactly {bleed_mm}mm from edge")
        print("  * Line is pure magenta (C=0, M=100, Y=0, K=0)")
        print("  * Path is a clean vector with 0.25pt width")
        print("  * No additional annotations or elements present")

if __name__ == "__main__":
    test_spot_color_cutlines() 