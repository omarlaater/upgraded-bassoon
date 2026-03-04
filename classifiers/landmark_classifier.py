import fnmatch
import os


LANDMARK_FILES = {
    "pom.xml": "Java",
    "build.gradle": "Java/Kotlin",
    "build.gradle.kts": "Kotlin",
    "package.json": "JavaScript/TypeScript",
    "requirements.txt": "Python",
    "pyproject.toml": "Python",
    "setup.py": "Python",
    "composer.json": "PHP",
}


class LandmarkClassifier:
    """Detects language hints using known landmark file names."""

    def classify(self, files, scores):
        # Backward-compatible helper kept for existing call sites.
        for path in files:
            lang = self.detect_language(path)
            if not lang:
                continue
            scores[lang] = scores.get(lang, 0) + 1
        return scores

    def detect_language(self, path: str) -> str | None:
        name = os.path.basename(path).lower()
        for pattern, lang in LANDMARK_FILES.items():
            if fnmatch.fnmatch(name, pattern):
                return lang
        return None
