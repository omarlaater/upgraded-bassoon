import os


EXT_MAP = {
    ".py": "Python",
    ".java": "Java",
    ".kt": "Kotlin",
    ".kts": "Kotlin",
    ".groovy": "Groovy",
    ".scala": "Scala",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".mjs": "JavaScript",
    ".cjs": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".cs": "C#",
    ".cpp": "C++",
    ".cc": "C++",
    ".cxx": "C++",
    ".h": "C/C++ Header",
    ".hpp": "C/C++ Header",
    ".c": "C",
    ".go": "Go",
    ".rs": "Rust",
    ".php": "PHP",
    ".rb": "Ruby",
    ".swift": "Swift",
    ".m": "Objective-C",
    ".mm": "Objective-C++",
    ".xml": "XML",
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".toml": "TOML",
    ".ini": "INI",
    ".properties": "Properties",
    ".sh": "Shell",
    ".bash": "Shell",
    ".zsh": "Shell",
    ".ps1": "PowerShell",
    ".sql": "SQL",
    ".html": "HTML",
    ".htm": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".sass": "Sass",
    ".less": "Less",
    ".dockerfile": "Dockerfile",
    ".md": "Markdown",
    ".txt": "Text",
    ".env": "Env",
}


class ExtensionClassifier:
    """Maps filename extensions to human-readable language labels."""

    def classify(self, files, scores):
        # Backward-compatible helper kept for existing call sites.
        for path in files:
            language = self.detect_language(path)
            if not language:
                language = self.unknown_extension_label(path)
            if not language:
                continue
            scores[language] = scores.get(language, 0) + 1
        return scores

    def detect_language(self, path: str) -> str | None:
        _, ext = os.path.splitext(path)
        ext = ext.lower()
        if not ext:
            return None

        language = EXT_MAP.get(ext)
        return language

    def unknown_extension_label(self, path: str) -> str | None:
        """Return a stable label for unmapped extensions."""
        _, ext = os.path.splitext(path)
        ext = ext.lower()
        if not ext:
            return None
        if ext in EXT_MAP:
            return None
        return f"Extension:{ext.strip('.')}"
