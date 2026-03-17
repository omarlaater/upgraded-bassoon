import os
from pathlib import Path

try:
    import yaml
except ImportError as exc:
    raise RuntimeError(
        "PyYAML is required to load classifiers/languages.yaml. "
        "Install it with: pip install pyyaml"
    ) from exc


TYPE_PRIORITY = {
    "programming": 0,
    "markup": 1,
    "data": 2,
    "prose": 3,
}

# Shared extensions need deterministic handling when Linguist lists multiple
# candidates. A `None` value means "too ambiguous, do not auto-classify".
AMBIGUOUS_EXTENSION_DEFAULTS = {
    ".cls": "Apex",
    ".h": None,
    ".json": "JSON",
    ".m": None,
    ".md": "Markdown",
    ".mm": "Objective-C++",
    ".pl": "Perl",
    ".sql": "SQL",
    ".ts": "TypeScript",
    ".xml": "XML",
    ".yaml": "YAML",
    ".yml": "YAML",
}


class ExtensionClassifier:
    """Maps filenames and extensions to Linguist language labels."""

    def __init__(self, languages_path: str | None = None):
        if languages_path:
            path = Path(languages_path)
        else:
            path = Path(__file__).with_name("languages.yaml")

        self.languages_path = path
        self.language_metadata = {}
        self.filename_map = {}
        self.extension_map = {}
        self.interpreter_map = {}
        self._load_linguist_data()

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

    def detect_language(self, path: str, interpreter: str | None = None) -> str | None:
        filename = os.path.basename(path).lower()
        if filename:
            language = self.filename_map.get(filename)
            if language:
                return language

        if interpreter:
            language = self.interpreter_map.get(interpreter.lower())
            if language:
                return language

        _, ext = os.path.splitext(path)
        ext = ext.lower()
        if not ext:
            return None

        candidates = self.extension_map.get(ext, [])
        return self._resolve_candidates(candidates, ext)

    def unknown_extension_label(self, path: str) -> str | None:
        """Return a stable label for unmapped extensions."""
        _, ext = os.path.splitext(path)
        ext = ext.lower()
        if not ext or ext in self.extension_map:
            return None
        return f"Extension:{ext.strip('.')}"

    def has_known_extension(self, path: str) -> bool:
        """Return True when the file extension exists in the Linguist extension map."""
        _, ext = os.path.splitext(path)
        return bool(ext and ext.lower() in self.extension_map)

    def has_known_filename(self, path: str) -> bool:
        """Return True when the basename exists in the Linguist filename map."""
        filename = os.path.basename(path).lower()
        return bool(filename and filename in self.filename_map)

    def get_language_type(self, language: str) -> str:
        """Return the Linguist type for a resolved language label."""
        metadata = self.language_metadata.get(language, {})
        return str(metadata.get("type", "") or "")

    def is_programming_language(self, language: str) -> bool:
        """Return True when Linguist marks the language as programming."""
        return self.get_language_type(language) == "programming"

    def _load_linguist_data(self) -> None:
        with self.languages_path.open("r", encoding="utf8") as stream:
            raw_languages = yaml.safe_load(stream) or {}

        self.language_metadata = {
            language: metadata or {}
            for language, metadata in raw_languages.items()
        }

        filename_candidates = {}
        extension_candidates = {}
        interpreter_candidates = {}

        for language, metadata in self.language_metadata.items():
            canonical_language = metadata.get("group") or language

            for filename in metadata.get("filenames", []) or []:
                filename_key = filename.lower()
                filename_candidates.setdefault(filename_key, []).append(canonical_language)

            for ext in metadata.get("extensions", []) or []:
                ext_key = ext.lower()
                extension_candidates.setdefault(ext_key, []).append(canonical_language)

            for interpreter in metadata.get("interpreters", []) or []:
                interpreter_key = interpreter.lower()
                interpreter_candidates.setdefault(interpreter_key, []).append(
                    canonical_language
                )

        self.filename_map = {
            filename: self._resolve_candidates(candidates)
            for filename, candidates in filename_candidates.items()
        }
        self.extension_map = {
            ext: sorted(set(candidates))
            for ext, candidates in extension_candidates.items()
        }
        self.interpreter_map = {
            interpreter: self._resolve_candidates(candidates)
            for interpreter, candidates in interpreter_candidates.items()
        }

    def _resolve_candidates(
        self,
        candidates: list[str],
        ext: str | None = None,
    ) -> str | None:
        if not candidates:
            return None

        normalized_candidates = sorted(set(candidates))
        if len(normalized_candidates) == 1:
            return normalized_candidates[0]

        if ext:
            if ext in AMBIGUOUS_EXTENSION_DEFAULTS:
                override = AMBIGUOUS_EXTENSION_DEFAULTS[ext]
                if override is None:
                    return None
                if override in normalized_candidates:
                    return override

        def sort_key(language: str) -> tuple[int, int, str]:
            metadata = self.language_metadata.get(language, {})
            language_type = metadata.get("type", "")
            return (TYPE_PRIORITY.get(language_type, 99), len(language), language)

        return sorted(normalized_candidates, key=sort_key)[0]
