from PIL import Image
import os
from flask import Flask, request, send_file
import zipfile
import tempfile

app = Flask(__name__)

def trim_whitespace(image):
    image = image.convert("RGBA")
    bbox = image.getbbox()
    return image.crop(bbox) if bbox else image

def generate_name_image(name, style_dirs, output_path, height=400, spacing=-5, transparent=True):
    # Load and trim letter images with alternating styles
    letter_images = []
    for i, letter in enumerate(name.upper()):
        style_dir = style_dirs[i % len(style_dirs)]
        path = os.path.join(style_dir, f"{letter}.png")
        img = Image.open(path)
        trimmed = trim_whitespace(img)

        # Resize to target height
        aspect_ratio = trimmed.width / trimmed.height
        new_width = int(height * aspect_ratio)
        resized = trimmed.resize((new_width, height), Image.Resampling.LANCZOS)
        letter_images.append(resized)

    # Calculate total image width
    total_width = sum(img.width for img in letter_images) + spacing * (len(letter_images) - 1)
    bg_color = (255, 255, 255, 0) if transparent else (255, 255, 255, 255)
    canvas = Image.new("RGBA", (total_width, height), bg_color)

    # Paste letters with tight spacing
    x_offset = 0
    for i, img in enumerate(letter_images):
        canvas.paste(img, (x_offset, 0), img)
        x_offset += img.width
        if i < len(letter_images) - 1:
            x_offset += spacing

    canvas.save(output_path)
    return output_path

@app.route('/generate', methods=['POST'])
def generate():
    name = request.form['name']
    height = int(request.form.get('height', 400))
    transparent = request.form.get('transparent', 'true').lower() == 'true'

    # Save ZIPs and extract
    style_dirs = []
    for i in range(1, 4):
        zip_file = request.files.get(f'style{i}')
        if not zip_file:
            continue
        temp_dir = tempfile.mkdtemp()
        with zipfile.ZipFile(zip_file, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        style_dirs.append(temp_dir)

    output_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png").name
import os

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
