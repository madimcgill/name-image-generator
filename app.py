from PIL import Image
import os
from flask import Flask, request, send_file
import zipfile
import tempfile

app = Flask(__name__)

def trim_whitespace(image):
    image = image.convert("RGBA")
    datas = image.getdata()

    # Find bounds of non-transparent pixels
    non_empty_pixels = [
        (x % image.width, x // image.width)
        for x, pixel in enumerate(datas)
        if pixel[3] > 0
    ]
    if not non_empty_pixels:
        return image  # Return as-is if nothing found

    xs, ys = zip(*non_empty_pixels)
    bbox = (min(xs), min(ys), max(xs)+1, max(ys)+1)
    return image.crop(bbox)

def extract_and_flatten_zip(zip_file, label):
    temp_dir = tempfile.mkdtemp()
    app.logger.info(f"[extract] Extracting {label} to: {temp_dir}")

    with zipfile.ZipFile(zip_file, 'r') as zip_ref:
        zip_ref.extractall(temp_dir)

    entries = os.listdir(temp_dir)
    app.logger.info(f"[extract] Top-level entries in {label}: {entries}")

    if len(entries) == 1 and os.path.isdir(os.path.join(temp_dir, entries[0])):
        temp_dir = os.path.join(temp_dir, entries[0])
        app.logger.info(f"[extract] Nested folder found in {label}, entering: {temp_dir}")

    app.logger.info(f"[extract] Final path for {label}: {temp_dir}")
    app.logger.info(f"[extract] Files in final path: {os.listdir(temp_dir)}")

    return temp_dir

def generate_name_image(name, style_dirs, output_path, height=400, spacing=-15, transparent=True):
    letter_images = []
    for i, letter in enumerate(name.upper()):
        style_dir = style_dirs[i % len(style_dirs)]
        candidates = [f"{letter}.png", f"{letter.lower()}.png"]
        
        found = False
        for filename in candidates:
            path = os.path.join(style_dir, filename)
            if os.path.exists(path):
                found = True
                app.logger.info(f"[build] Using: {path}")
                img = Image.open(path)
                trimmed = trim_whitespace(img)
                aspect_ratio = trimmed.width / trimmed.height
                new_width = int(height * aspect_ratio)
                resized = trimmed.resize((new_width, height), Image.Resampling.LANCZOS)
                letter_images.append(resized)
                break

        if not found:
            raise FileNotFoundError(f"[build] Missing letter: {letter} in style {i % len(style_dirs) + 1}")

        img = Image.open(path)
        trimmed = trim_whitespace(img)

        aspect_ratio = trimmed.width / trimmed.height
        new_width = int(height * aspect_ratio)
        resized = trimmed.resize((new_width, height), Image.Resampling.LANCZOS)
        letter_images.append(resized)

    total_width = sum(img.width for img in letter_images) + spacing * (len(letter_images) - 1)
    bg_color = (255, 255, 255, 0) if transparent else (255, 255, 255, 255)
    canvas = Image.new("RGBA", (total_width, height), bg_color)

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
    app.logger.info(f"[request] Name: {name}, Height: {height}, Transparent: {transparent}")

    style_dirs = []
    for i in range(1, 4):
        zip_file = request.files.get(f'style{i}')
        if not zip_file:
            app.logger.info(f"[request] style{i} ZIP not provided")
            continue
        extracted_dir = extract_and_flatten_zip(zip_file, f"style{i}")
        style_dirs.append(extracted_dir)

    output_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png").name
    try:
        result_path = generate_name_image(name, style_dirs, output_file, height=height, transparent=transparent)
        return send_file(result_path, mimetype='image/png')
    except Exception as e:
        app.logger.info(f"[error] {e}")
        return f"Error generating image: {e}", 400

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 5001))
    app.run(host='0.0.0.0', port=port)

# debug redeploy trigger
