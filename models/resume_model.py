"""Resume business rules. No HTTP or HTML dependencies."""
import json
import re
from pathlib import Path
from models.mongo_database import MONGO_URI, skill_aliases

def catalogue():
    if MONGO_URI:
        return skill_aliases()
    path = Path(__file__).resolve().parents[1] / 'data/skills.json'
    return json.loads(path.read_text(encoding='utf-8'))

def extract_skills(text):
    return [skill for skill, aliases in catalogue().items() if any(
        re.search(r'(?<![a-z0-9])' + re.escape(alias) + r'(?![a-z0-9])', text, re.I)
        for alias in aliases)]
