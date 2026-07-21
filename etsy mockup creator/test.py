import re

def parse_prompt_file(filepath):
    prompts = []

    current_category = "unknown"

    category_map = {
        "main_character": "MAIN_CHARACTER",
        "main character": "MAIN_CHARACTER",
        "sub_character_1": "SUB_CHARACTER_1",
        "sub character 1": "SUB_CHARACTER_1",
        "sub_character_2": "SUB_CHARACTER_2",
        "sub character 2": "SUB_CHARACTER_2",
        "sub_character_3": "SUB_CHARACTER_3",
        "sub character 3": "SUB_CHARACTER_3",
        "sub_character_4": "SUB_CHARACTER_4",
        "sub character 4": "SUB_CHARACTER_4",
        "sub_character_5": "SUB_CHARACTER_5",
        "sub character 5": "SUB_CHARACTER_5",
        "sub_character_6": "SUB_CHARACTER_6",
        "sub character 6": "SUB_CHARACTER_6",
        "sub_character_7": "SUB_CHARACTER_7",
        "sub character 7": "SUB_CHARACTER_7",
        "sub_character_8": "SUB_CHARACTER_8",
        "sub character 8": "SUB_CHARACTER_8",
        "character_combo_2": "CHARACTER_COMBO_2",
        "character combo 2": "CHARACTER_COMBO_2",
        "character_combo_3": "CHARACTER_COMBO_3",
        "character combo 3": "CHARACTER_COMBO_3",
        "character_combo_4": "CHARACTER_COMBO_4",
        "character combo 4": "CHARACTER_COMBO_4",
        "character_combo_full_group": "CHARACTER_COMBO_FULL_GROUP",
        "character combo full group": "CHARACTER_COMBO_FULL_GROUP",
        "pattern": "PATTERN",
        "prop": "PROP",
        "scene": "SCENE",
        "logo_emblem": "LOGO_EMBLEM",
        "logo emblem": "LOGO_EMBLEM",
        "banner": "BANNER",
        "alphabet_number": "ALPHABET_NUMBER",
        "alphabet number": "ALPHABET_NUMBER",
        "frame_border": "FRAME_BORDER",
        "frame border": "FRAME_BORDER"
    }

    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Sort map keys by length descending to match most specific terms first
    sorted_map = sorted(category_map.items(), key=lambda x: len(x[0]), reverse=True)

    for line in lines:
        text = line.strip()
        if not text:
            continue

        lower = text.lower()

        # Detect category headings starting with ## or containing 'category'
        if text.startswith("##") or "category" in lower:
            header_text = text.lstrip("#").strip().lower()
            detected = None
            for key, value in sorted_map:
                if key in header_text:
                    detected = value
                    break

            if detected:
                current_category = detected
            continue

        # Detect numbered prompts
        match = re.match(r"^\d+\.\s+(.*)", text)
        if match:
            prompts.append({
                "category": current_category,
                "prompt": match.group(1)
            })

    return prompts


# import re

# def parse_prompt_file(filepath):
#     prompts = []

#     current_category = "unknown"

#     category_map = {
#         "solo": "character",
#         "main_character": "character",
#         "sub character": "subcharacter",
#         "sub_character": "subcharacter",
#         "combo": "combo",
#         "multi-character": "combo",
#         "pattern": "pattern",
#         "prop": "prop",
#         "object": "prop",
#         "item": "prop",
#         "scene": "scene",
#         "background": "scene",
#         "location": "scene",
#         "bonus": "bonus"
#     }

#     with open(filepath, "r", encoding="utf-8") as f:
#         lines = f.readlines()

#     for line in lines:

#         text = line.strip()

#         if not text:
#             continue

#         lower = text.lower()

#         # Detect category headings
#         if "category" in lower:

#             detected = None

#             for key, value in category_map.items():
#                 if key in lower:
#                     detected = value
#                     break

#             if detected:
#                 current_category = detected

#             continue

#         # Detect numbered prompts
#         match = re.match(r"^\d+\.\s+(.*)", text)

#         if match:

#             prompts.append({
#                 "category": current_category,
#                 "prompt": match.group(1)
#             })

#     return prompts

parse = parse_prompt_file("sam.txt")
print(parse)