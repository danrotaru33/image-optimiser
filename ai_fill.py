from gradio_client import Client, handle_file
import os

def ai_fill_margins(input_path: str, width: int, height: int) -> str:
    try:
        client = Client("danrotaru33/daisler-image-optimiser")
        result = client.predict(
            image=handle_file(input_path),
            width=width,
            height=height,
            overlap_percentage=10,
            num_inference_steps=8,
            resize_option="Full",
            custom_resize_percentage=50,
            prompt_input="Extend margin",
            alignment="Middle",
            overlap_left=True,
            overlap_right=True,
            overlap_top=True,
            overlap_bottom=True,
            api_name="/infer"
        )
        # Save the result image locally
        output_path = input_path.replace('.pdf', '_aifill.png')
        if hasattr(result, 'save'):
            result.save(output_path)
        elif isinstance(result, str) and os.path.exists(result):
            os.rename(result, output_path)
        else:
            # If result is a PIL Image
            try:
                from PIL import Image
                if isinstance(result, Image.Image):
                    result.save(output_path)
            except ImportError:
                pass
        return output_path
    except Exception as e:
        print(f"AI fill failed: {e}")
        return input_path
