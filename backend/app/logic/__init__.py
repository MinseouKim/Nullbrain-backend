import json
from pathlib import Path

def load_dummy_profile():
    """더미 JSON 불러오기"""
    path = Path(__file__).resolve().parent / "dummy_profile.json"
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)