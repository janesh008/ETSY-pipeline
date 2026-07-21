import json
import os
from typing import Any, Dict, List

class TemplateLoader:
    """
    Loads, validates, and stores Etsy mockup JSON templates.
    """
    @staticmethod
    def load_template(template_path: str) -> Dict[str, Any]:
        """
        Loads a single template JSON file and returns its parsed dictionary representation.
        """
        if not os.path.isfile(template_path):
            raise FileNotFoundError(f"Template file '{template_path}' not found.")
            
        with open(template_path, "r", encoding="utf-8") as f:
            try:
                template_data = json.load(f)
            except json.JSONDecodeError as e:
                raise ValueError(f"Failed to parse JSON in '{template_path}': {e}")
                
        # Basic validation
        if "name" not in template_data:
            raise ValueError(f"Template '{template_path}' is missing the 'name' field.")
        if "canvas_size" not in template_data:
            raise ValueError(f"Template '{template_path}' is missing the 'canvas_size' field.")
        if "elements" not in template_data:
            raise ValueError(f"Template '{template_path}' is missing the 'elements' field.")
            
        return template_data

    @staticmethod
    def load_all_templates(templates_dir: str) -> List[Dict[str, Any]]:
        """
        Loads all template JSON files in a directory.
        """
        if not os.path.isdir(templates_dir):
            raise FileNotFoundError(f"Templates directory '{templates_dir}' does not exist.")
            
        templates = []
        for file_entry in os.scandir(templates_dir):
            if file_entry.is_file() and file_entry.name.lower().endswith(".json"):
                try:
                    templates.append(TemplateLoader.load_template(file_entry.path))
                except Exception as e:
                    print(f"Warning: Skipping template '{file_entry.name}' due to error: {e}")
        return templates
