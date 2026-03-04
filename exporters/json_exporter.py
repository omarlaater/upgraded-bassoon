import json


def save_json(results, path):
    """Persist full nested repository report to JSON."""
    with open(path, "w", encoding="utf8") as f:
        json.dump(results, f, indent=2)

    print("JSON saved:", path)
