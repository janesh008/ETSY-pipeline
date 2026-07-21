import os
from PIL import Image, ImageDraw

def create_dummy_png(path: str, name: str, bg_color: tuple, shape_type: str):
    """
    Creates a transparent PNG with a simple colored geometric shape.
    """
    img = Image.new("RGBA", (800, 800), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    if shape_type == "circle":
        draw.ellipse([100, 100, 700, 700], fill=bg_color, outline=(255, 255, 255, 255), width=10)
    elif shape_type == "square":
        draw.rectangle([150, 150, 650, 650], fill=bg_color, outline=(255, 255, 255, 255), width=10)
    elif shape_type == "star":
        # simple diamond / star outline
        draw.polygon([(400, 100), (700, 400), (400, 700), (100, 400)], fill=bg_color)
    else: # scene
        # Full solid background
        draw.rectangle([0, 0, 800, 800], fill=bg_color)
        draw.ellipse([200, 200, 600, 600], fill=(255, 255, 255, 100))
        
    # Draw simple label
    draw.text((400, 400), name, fill=(255, 255, 255, 255), anchor="mm")
    
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path, "PNG")

def main():
    base_dir = os.path.join("tests", "sample_theme")
    print(f"Generating dummy theme assets at: {base_dir}")
    
    # 1. Characters
    create_dummy_png(os.path.join(base_dir, "character", "character_001.png"), "Simba (Char 1)", (217, 130, 43, 255), "circle")
    create_dummy_png(os.path.join(base_dir, "character", "character_002.png"), "Nala (Char 2)", (240, 210, 150, 255), "circle")
    create_dummy_png(os.path.join(base_dir, "character", "character_003.png"), "Timon (Char 3)", (170, 120, 80, 255), "circle")
    create_dummy_png(os.path.join(base_dir, "character", "character_004.png"), "Pumbaa (Char 4)", (140, 70, 50, 255), "circle")
    create_dummy_png(os.path.join(base_dir, "character", "character_005.png"), "Rafiki (Char 5)", (100, 140, 190, 255), "circle")
    create_dummy_png(os.path.join(base_dir, "character", "character_006.png"), "Mufasa (Char 6)", (200, 100, 50, 255), "circle")

    # 2. Combos
    create_dummy_png(os.path.join(base_dir, "combo", "combo_001.png"), "Simba & Nala (Combo 1)", (230, 170, 100, 255), "star")
    create_dummy_png(os.path.join(base_dir, "combo", "combo_002.png"), "Timon & Pumbaa (Combo 2)", (150, 90, 60, 255), "star")

    # 3. Props
    create_dummy_png(os.path.join(base_dir, "prop", "prop_001.png"), "Baobab Tree", (120, 150, 100, 255), "square")
    create_dummy_png(os.path.join(base_dir, "prop", "prop_002.png"), "Jungle Leaf", (46, 125, 50, 255), "square")
    create_dummy_png(os.path.join(base_dir, "prop", "prop_003.png"), "Pride Rock", (140, 140, 140, 255), "square")
    create_dummy_png(os.path.join(base_dir, "prop", "prop_004.png"), "Sun Icon", (255, 193, 7, 255), "square")
    create_dummy_png(os.path.join(base_dir, "prop", "prop_005.png"), "Bugs Combo", (190, 100, 190, 255), "square")
    create_dummy_png(os.path.join(base_dir, "prop", "prop_006.png"), "Cave Art", (160, 120, 90, 255), "square")

    # 4. Patterns
    create_dummy_png(os.path.join(base_dir, "pattern", "pattern_001.png"), "Safar Pattern", (255, 235, 200, 255), "scene")
    create_dummy_png(os.path.join(base_dir, "pattern", "pattern_002.png"), "Leaf Pattern", (200, 230, 201, 255), "scene")
    create_dummy_png(os.path.join(base_dir, "pattern", "pattern_003.png"), "Paw Pattern", (248, 187, 208, 255), "scene")

    # 5. Scenes
    create_dummy_png(os.path.join(base_dir, "scene", "scene_001.png"), "Sunset Scene", (255, 112, 67, 255), "scene")

    print("Sample assets created successfully.")

if __name__ == "__main__":
    main()
