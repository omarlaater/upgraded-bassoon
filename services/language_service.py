"""Service layer: converts raw metadata into programming and file-type analytics."""

import os
from collections import defaultdict
from typing import Dict, List

from classifiers.extension_classifier import ExtensionClassifier
from classifiers.landmark_classifier import LandmarkClassifier


class LanguageService:
    """Transforms raw file metadata into programming and file-type distributions."""

    def __init__(
        self,
        extension_classifier: ExtensionClassifier | None = None,
        landmark_classifier: LandmarkClassifier | None = None,
    ):
        self.extension_classifier = extension_classifier or ExtensionClassifier()
        self.landmark_classifier = landmark_classifier or LandmarkClassifier()

    def build_language_reports(self, repository_payloads: List[Dict]) -> List[Dict]:
        return [self._build_one_report(payload) for payload in repository_payloads]

    def _build_one_report(self, repo_payload: Dict) -> Dict:
        language_sizes = defaultdict(int)
        language_files = defaultdict(int)
        file_type_sizes = defaultdict(int)
        file_type_files = defaultdict(int)
        file_type_types = {}
        extension_sizes = defaultdict(int)
        extension_files = defaultdict(int)

        repo_size_bytes = 0
        files = repo_payload.get("files", [])

        for file_info in files:
            path = file_info["path"]
            size_bytes = int(file_info.get("size_bytes", 0))
            repo_size_bytes += size_bytes
            extension = _normalize_extension(path)
            extension_sizes[extension] += size_bytes
            extension_files[extension] += 1

            language = self.extension_classifier.detect_language(path)
            if not language:
                language = self.landmark_classifier.detect_language(path)
            if language:
                language_type = self.extension_classifier.get_language_type(language)
                normalized_type = language_type or "programming"
                file_type_sizes[language] += size_bytes
                file_type_files[language] += 1
                file_type_types[language] = normalized_type
                if normalized_type == "programming":
                    language_sizes[language] += size_bytes
                    language_files[language] += 1

        programming_size_bytes = sum(language_sizes.values())
        file_type_size_bytes = sum(file_type_sizes.values())
        extension_size_bytes = sum(extension_sizes.values())
        distribution = []
        for language, size_bytes in sorted(
            language_sizes.items(),
            key=lambda item: item[1],
            reverse=True,
        ):
            percentage = (
                (size_bytes / programming_size_bytes * 100.0)
                if programming_size_bytes
                else 0.0
            )
            distribution.append(
                {
                    "language": language,
                    "language_size_bytes": size_bytes,
                    "file_count": language_files[language],
                    "language_percentage": round(percentage, 2),
                }
            )

        file_type_distribution = []
        for language, size_bytes in sorted(
            file_type_sizes.items(),
            key=lambda item: item[1],
            reverse=True,
        ):
            percentage = (
                (size_bytes / file_type_size_bytes * 100.0)
                if file_type_size_bytes
                else 0.0
            )
            file_type = file_type_types.get(language, "programming")
            file_type_distribution.append(
                {
                    "language": language,
                    "type": file_type,
                    "size_bytes": size_bytes,
                    "file_count": file_type_files[language],
                    "percentage": round(percentage, 2),
                    "eligible_for_primary": file_type == "programming",
                }
            )

        extension_distribution = []
        for extension, size_bytes in sorted(
            extension_sizes.items(),
            key=lambda item: item[1],
            reverse=True,
        ):
            percentage = (
                (size_bytes / extension_size_bytes * 100.0)
                if extension_size_bytes
                else 0.0
            )
            extension_distribution.append(
                {
                    "extension": extension,
                    "size_bytes": size_bytes,
                    "file_count": extension_files[extension],
                    "percentage": round(percentage, 2),
                }
            )

        primary_language = distribution[0]["language"] if distribution else "Unknown"
        return {
            "project_key": repo_payload["project_key"],
            "project_name": repo_payload["project_name"],
            "repo_slug": repo_payload["repo_slug"],
            "repo_name": repo_payload["repo_name"],
            "clone_url": repo_payload.get("clone_url", ""),
            "repo_created_date_raw": repo_payload.get("repo_created_date_raw", ""),
            "repo_created_date_utc": repo_payload.get("repo_created_date_utc", ""),
            # Branch metadata is collected in collector and forwarded by service.
            "default_branch": repo_payload.get("default_branch", ""),
            "branch_count": int(repo_payload.get("branch_count", 0)),
            "branches_truncated": bool(repo_payload.get("branches_truncated", False)),
            "branches": repo_payload.get("branches", []),
            "repo_size_bytes": repo_size_bytes,
            "programming_size_bytes": programming_size_bytes,
            "file_type_size_bytes": file_type_size_bytes,
            "extension_size_bytes": extension_size_bytes,
            "primary_language": primary_language,
            "language_distribution": distribution,
            "file_type_distribution": file_type_distribution,
            "extension_distribution": extension_distribution,
            "errors": repo_payload.get("errors", []),
        }


def print_summary(results: List[Dict]) -> None:
    """Print global size-bytes summary across all repositories."""
    totals = defaultdict(int)
    file_type_totals = defaultdict(int)
    file_type_labels = {}
    total_bytes = 0
    total_programming_bytes = 0
    total_file_type_bytes = 0
    total_branches = 0

    for repo in results:
        total_bytes += int(repo.get("repo_size_bytes", 0))
        total_programming_bytes += int(repo.get("programming_size_bytes", 0))
        total_file_type_bytes += int(repo.get("file_type_size_bytes", 0))
        total_branches += int(repo.get("branch_count", 0))
        for lang_data in repo.get("language_distribution", []):
            language = lang_data["language"]
            totals[language] += int(lang_data.get("language_size_bytes", 0))
        for file_type_data in repo.get("file_type_distribution", []):
            language = file_type_data["language"]
            file_type_totals[language] += int(file_type_data.get("size_bytes", 0))
            file_type_labels[language] = file_type_data.get("type", "")

    print("\nProgramming Language Summary (by bytes)")
    for language, size_bytes in sorted(
        totals.items(),
        key=lambda x: x[1],
        reverse=True,
    ):
        pct = (size_bytes / total_programming_bytes * 100.0) if total_programming_bytes else 0.0
        print(f"{language:24} {human_size(size_bytes):>10} {pct:6.2f}%")

    if file_type_totals:
        print("\nDetected File Type Summary (recognized bytes)")
        for language, size_bytes in sorted(
            file_type_totals.items(),
            key=lambda x: x[1],
            reverse=True,
        ):
            pct = (size_bytes / total_file_type_bytes * 100.0) if total_file_type_bytes else 0.0
            label = file_type_labels.get(language, "")
            display_name = f"{language} [{label}]" if label else language
            print(f"{display_name:24} {human_size(size_bytes):>10} {pct:6.2f}%")

    print(f"\nTotal repos: {len(results)}")
    print(f"Total bytes: {human_size(total_bytes)}")
    print(f"Total programming bytes: {human_size(total_programming_bytes)}")
    print(f"Total recognized file-type bytes: {human_size(total_file_type_bytes)}")
    print(f"Total branches discovered: {total_branches}")

    extension_totals = defaultdict(int)
    total_extension_bytes = 0
    for repo in results:
        total_extension_bytes += int(repo.get("extension_size_bytes", 0))
        for ext_data in repo.get("extension_distribution", []):
            extension = ext_data["extension"]
            extension_totals[extension] += int(ext_data.get("size_bytes", 0))

    if extension_totals:
        print("\nTop Extensions (by bytes)")
        for extension, size_bytes in sorted(
            extension_totals.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:10]:
            pct = (size_bytes / total_extension_bytes * 100.0) if total_extension_bytes else 0.0
            print(f"{extension:24} {human_size(size_bytes):>10} {pct:6.2f}%")


def human_size(size_bytes: int) -> str:
    """Convert byte counts to human-readable units."""
    if size_bytes < 1024:
        return f"{size_bytes} B"

    size = float(size_bytes)
    for unit in ["KB", "MB", "GB", "TB"]:
        size /= 1024.0
        if size < 1024.0:
            return f"{size:.2f} {unit}"
    return f"{size:.2f} PB"


def _fallback_no_extension_label() -> str:
    return "(no_extension)"


def _normalize_extension(path: str) -> str:
    _, ext = os.path.splitext(path)
    ext = ext.lower()
    return ext or _fallback_no_extension_label()
