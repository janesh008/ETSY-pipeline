import os
import sys
import json
import re
import urllib.request
import urllib.parse
from flask import Flask, request, jsonify, send_file, send_from_directory

# Add project root to path to import src modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.generator import Generator

app = Flask(__name__, static_folder="static", static_url_path="")

# Globals
MASTER_DIR = ""

# ─────────────────────────────────────────────────────────────────────────────
# Static files routing
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")

# ─────────────────────────────────────────────────────────────────────────────
# Folder Selection & Navigation
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/api/select-master", methods=["POST"])
def select_master():
    global MASTER_DIR
    
    try:
        data = request.json or {}
        folder_path = data.get("path")
        
        if not folder_path:
            return jsonify({"error": "No directory path provided"}), 400
            
        if not os.path.isdir(folder_path):
            return jsonify({"error": f"Directory does not exist: {folder_path}"}), 400
            
        # Normalize path
        folder_path = os.path.abspath(folder_path).replace("\\", "/")
        MASTER_DIR = folder_path
        
        # Read subfolders
        subfolders = []
        for entry in os.scandir(folder_path):
            if entry.is_dir() and not entry.name.startswith("."):
                # Count images in subfolder
                count = sum(1 for file in os.scandir(entry.path) if file.is_file() and file.name.lower().endswith(".png"))
                subfolders.append({
                    "name": entry.name,
                    "path": entry.name,
                    "image_count": count
                })
                
        return jsonify({
            "master_path": folder_path,
            "subfolders": sorted(subfolders, key=lambda x: x["name"])
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/folder-contents", methods=["GET"])
def get_folder_contents():
    global MASTER_DIR
    if not MASTER_DIR:
        return jsonify({"error": "Master folder not selected"}), 400
        
    rel_path = request.args.get("folder_relative_path", "")
    
    # Normalize both paths to use forward slashes to prevent Windows path mismatch
    master_norm = os.path.abspath(MASTER_DIR).replace("\\", "/")
    target_dir = os.path.abspath(os.path.join(master_norm, rel_path)).replace("\\", "/")
    
    # Security check: ensure target_dir is inside master_norm
    if not target_dir.startswith(master_norm):
        return jsonify({"error": "Unauthorized path access"}), 403
        
    if not os.path.exists(target_dir):
        return jsonify({"error": "Folder not found"}), 404
        
    images = []
    for entry in os.scandir(target_dir):
        if entry.is_file() and entry.name.lower().endswith(".png"):
            images.append({
                "name": entry.name,
                "url": f"/api/image?path={urllib.parse.quote(entry.path.replace('\\', '/'))}"
            })
            
    return jsonify({
        "current_path": rel_path,
        "images": sorted(images, key=lambda x: x["name"])
    })


@app.route("/api/image", methods=["GET"])
def serve_image():
    global MASTER_DIR
    img_path = request.args.get("path")
    category = request.args.get("category")
    index_param = request.args.get("index")
    size_param = request.args.get("size")
    
    # If category and index are provided, resolve the real file path inside the master theme directory
    if category and index_param is not None and MASTER_DIR:
        try:
            index = int(index_param)
            target_dir = os.path.abspath(os.path.join(MASTER_DIR, category)).replace("\\", "/")
            if os.path.exists(target_dir):
                files = [entry.path for entry in os.scandir(target_dir) if entry.is_file() and entry.name.lower().endswith(".png")]
                files.sort()
                if files:
                    img_path = files[index % len(files)]
        except Exception as e:
            print(f"Error resolving category {category} index {index_param}: {e}")
            
    if not img_path or not os.path.exists(img_path):
        return "Image not found", 404
        
    if size_param:
        try:
            size = int(size_param)
            from PIL import Image
            import io
            
            img = Image.open(img_path)
            # Maintain aspect ratio
            img.thumbnail((size, size))
            
            img_io = io.BytesIO()
            img.save(img_io, "PNG")
            img_io.seek(0)
            return send_file(img_io, mimetype="image/png")
        except Exception as e:
            print(f"Error generating thumbnail for {img_path}: {e}")
            
    return send_file(img_path, mimetype="image/png")

# ─────────────────────────────────────────────────────────────────────────────
# Template Load & Save
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/api/templates", methods=["GET"])
def list_templates():
    templates_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "templates"))
    os.makedirs(templates_dir, exist_ok=True)
    
    templates = []
    for entry in os.scandir(templates_dir):
        if entry.is_file() and entry.name.lower().endswith(".json"):
            try:
                with open(entry.path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                templates.append({
                    "filename": entry.name,
                    "name": data.get("name", entry.name),
                    "canvas_size": data.get("canvas_size", [2000, 2000])
                })
            except Exception as e:
                print(f"Error loading template {entry.name}: {e}")
                
    return jsonify(sorted(templates, key=lambda x: x["filename"]))


@app.route("/api/templates/<filename>", methods=["GET"])
def load_template(filename):
    template_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "templates", filename))
    if not os.path.exists(template_path):
        return jsonify({"error": "Template not found"}), 404
        
    try:
        with open(template_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/templates/<filename>", methods=["POST"])
def save_template(filename):
    template_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "templates", filename))
    data = request.json
    
    try:
        with open(template_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return jsonify({"success": True, "message": f"Saved {filename}!"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ─────────────────────────────────────────────────────────────────────────────
# Google Fonts Dynamic Download
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/api/fonts/download", methods=["POST"])
def download_font():
    data = request.json
    font_family = data.get("font_family")
    
    if not font_family:
        return jsonify({"error": "Font family not specified"}), 400
        
    fonts_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "fonts"))
    os.makedirs(fonts_dir, exist_ok=True)
    
    # Safe filename converter
    safe_name = font_family.replace(" ", "")
    regular_path = os.path.join(fonts_dir, f"{safe_name}-Regular.ttf")
    bold_path = os.path.join(fonts_dir, f"{safe_name}-Bold.ttf")
    
    if os.path.exists(regular_path) and os.path.exists(bold_path):
        return jsonify({"success": True, "message": f"Font {font_family} already downloaded."})
        
    try:
        # Request CSS from Google Fonts using a User-Agent that forces TTF
        # IE11/old Safari forces TTF instead of woff2
        url = f"https://fonts.googleapis.com/css2?family={urllib.parse.quote(font_family)}:wght@400;700"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.75.14 (KHTML, like Gecko) Version/7.0.3 Safari/7046A194A"
            }
        )
        
        with urllib.request.urlopen(req) as response:
            css = response.read().decode("utf-8")
            
        # Parse CSS to find font URLs
        # Format: src: url(https://...) format('truetype');
        matches = re.findall(r'src:\s*url\((https://[^)]+)\)\s*format\([\'"]truetype[\'"]\)', css)
        
        # If no explicit format('truetype') found, try matching any https URL containing .ttf
        if not matches:
            matches = re.findall(r'url\((https://[^)]+\.ttf)\)', css)
            
        # Or parse generic url(...) and check weights
        font_urls = re.findall(r'url\((https://[^)]+)\)', css)
        
        if not font_urls:
            return jsonify({"error": "Could not find font URLs in Google CSS"}), 404
            
        # Map regular and bold weights from the CSS blocks
        # Simply: download first matches
        downloaded = []
        
        # Regular: first url in css usually regular weight
        reg_url = font_urls[0]
        urllib.request.urlretrieve(reg_url, regular_path)
        downloaded.append(f"{safe_name}-Regular.ttf")
        
        # Bold: second url is usually bold if requested
        if len(font_urls) > 1:
            bold_url = font_urls[-1]
            urllib.request.urlretrieve(bold_url, bold_path)
            downloaded.append(f"{safe_name}-Bold.ttf")
        else:
            # Copy regular to bold if no bold exists
            import shutil
            shutil.copyfile(regular_path, bold_path)
            downloaded.append(f"{safe_name}-Bold.ttf (Copied from Regular)")
            
        # Create aliases for Pillow lookup compatibility (with spaces, direct TTF mappings)
        import shutil
        shutil.copyfile(regular_path, os.path.join(fonts_dir, f"{font_family}.ttf"))
        shutil.copyfile(regular_path, os.path.join(fonts_dir, f"{safe_name}.ttf"))
        shutil.copyfile(regular_path, os.path.join(fonts_dir, f"{font_family}-Regular.ttf"))
        shutil.copyfile(bold_path, os.path.join(fonts_dir, f"{font_family}-Bold.ttf"))
        
        return jsonify({
            "success": True,
            "message": f"Successfully downloaded: {', '.join(downloaded)} and created lookup aliases."
        })
    except Exception as e:
        return jsonify({"error": f"Failed to download Google Font: {str(e)}"}), 500


@app.route("/api/fonts/list", methods=["GET"])
def list_local_fonts():
    """Returns a list of all font files available in assets/fonts."""
    fonts_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "fonts"))
    if not os.path.isdir(fonts_dir):
        return jsonify({"fonts": []})
    
    fonts = []
    for entry in os.scandir(fonts_dir):
        if entry.is_file() and entry.name.lower().endswith((".ttf", ".otf")):
            name_no_ext = os.path.splitext(entry.name)[0]
            fonts.append({
                "filename": entry.name,
                "family": name_no_ext,
                "url": f"/api/fonts/file/{entry.name}"
            })
    return jsonify({"fonts": sorted(fonts, key=lambda x: x["family"])})


@app.route("/api/fonts/file/<filename>", methods=["GET"])
def serve_font_file(filename):
    """Serves a font file from assets/fonts for browser @font-face usage."""
    fonts_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "fonts"))
    font_path = os.path.join(fonts_dir, filename)
    
    if not os.path.exists(font_path):
        return "Font not found", 404
    
    mimetype = "font/ttf" if filename.lower().endswith(".ttf") else "font/otf"
    return send_file(font_path, mimetype=mimetype)

# ─────────────────────────────────────────────────────────────────────────────
# Mockup Generation / Preview
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/api/generate", methods=["POST"])
def generate_mockups():
    global MASTER_DIR
    if not MASTER_DIR:
        return jsonify({"error": "Master folder not selected"}), 400
        
    data = request.json
    template_data = data.get("template")
    template_filename = data.get("filename", "active_editing_template.json")
    
    if not template_data:
        return jsonify({"error": "Template data not specified"}), 400
        
    # Save the current state to a temp template
    templates_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "templates"))
    temp_path = os.path.join(templates_dir, template_filename)
    
    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(template_data, f, indent=2)
            
        # Output directory
        output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "pooh_gender_reveal_output"))
        os.makedirs(output_dir, exist_ok=True)
        
        # Run Generator for this single file
        from pathlib import Path
        import re
        
        path_obj = Path(MASTER_DIR)
        theme_folder_name = path_obj.name
        
        # If the selected folder is a known subfolder, use its parent name instead
        if theme_folder_name.lower() in ("processed_no_bg", "processed no bg", "processed-no-bg", "misc_category", "scen-pattern"):
            theme_folder_name = path_obj.parent.name
            
        clean_name = re.sub(r'[\s_\-]*\d+$', '', theme_folder_name)
        theme_name = clean_name.replace("_", " ")
        
        from src.image_loader import ImageLoader
        from src.renderer import Renderer
        
        indexed_images = ImageLoader.load_theme_images(MASTER_DIR)
        
        # Perform rendering
        canvas = Renderer.render_template(
            template_data, 
            theme_name, 
            indexed_images,
            template_name=template_filename
        )
        
        # Save output
        output_filename = os.path.splitext(template_filename)[0].capitalize() + ".png"
        output_path = os.path.join(output_dir, output_filename)
        canvas.save(output_path, "PNG")
        
        # Return path so it can be previewed or opened
        return jsonify({
            "success": True,
            "output_path": output_path,
            "filename": output_filename,
            "preview_url": f"/api/image?path={urllib.parse.quote(output_path.replace('\\', '/'))}&t={time_now()}"
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/api/batch-generate", methods=["POST"])
def run_batch_generate():
    try:
        data = request.json or {}
        batch_dir = data.get("batch_dir")
        
        if not batch_dir:
            return jsonify({"error": "No batch directory path provided"}), 400
            
        batch_path = os.path.abspath(batch_dir).replace("\\", "/")
        if not os.path.exists(batch_path) or not os.path.isdir(batch_path):
            return jsonify({"error": f"Batch directory does not exist: {batch_dir}"}), 400
            
        # Scan and find valid theme directories
        theme_dirs = []
        for entry in os.scandir(batch_path):
            if entry.is_dir() and not entry.name.startswith("."):
                has_png = False
                for root, dirs, files in os.walk(entry.path):
                    if any(f.lower().endswith(".png") for f in files):
                        has_png = True
                        break
                if has_png:
                    theme_dirs.append(entry)
                    
        if not theme_dirs:
            return jsonify({"error": "No valid theme folders found inside the main folder."}), 400
            
        templates_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "templates"))
        
        processed_themes = []
        for t in theme_dirs:
            theme_path = t.path
            output_path = os.path.join(theme_path, "etsy_mockups").replace("\\", "/")
            
            # Execute generation
            Generator.generate_all(
                theme_dir=theme_path,
                templates_dir=templates_dir,
                output_dir=output_path
            )
            processed_themes.append(t.name)
            
        return jsonify({
            "success": True,
            "message": f"Batch generation complete! Successfully processed {len(processed_themes)} themes.",
            "processed_themes": processed_themes
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

def time_now():
    import time
    return int(time.time())

# ─────────────────────────────────────────────────────────────────────────────
# Server Execution
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
