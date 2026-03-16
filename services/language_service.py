"""Service layer: converts raw metadata into language distribution analytics."""

from collections import defaultdict
from typing import Dict, List

from classifiers.extension_classifier import ExtensionClassifier
from classifiers.file_kind_classifier import FileKindClassifier
from classifiers.landmark_classifier import LandmarkClassifier


class LanguageService:
    """Transforms raw file metadata into language and file-kind distributions."""

    def __init__(
        self,
        extension_classifier: ExtensionClassifier | None = None,
        file_kind_classifier: FileKindClassifier | None = None,
        landmark_classifier: LandmarkClassifier | None = None,
    ):
        self.extension_classifier = extension_classifier or ExtensionClassifier()
        self.file_kind_classifier = file_kind_classifier or FileKindClassifier()
        self.landmark_classifier = landmark_classifier or LandmarkClassifier()

    def build_language_reports(self, repository_payloads: List[Dict]) -> List[Dict]:
        return [self._build_one_report(payload) for payload in repository_payloads]

    def _build_one_report(self, repo_payload: Dict) -> Dict:
        language_sizes = defaultdict(int)
        language_files = defaultdict(int)
        file_kind_sizes = defaultdict(int)
        file_kind_files = defaultdict(int)
        unknown_sizes = defaultdict(int)
        unknown_files = defaultdict(int)

        repo_size_bytes = 0
        files = repo_payload.get("files", [])

        for file_info in files:
            path = file_info["path"]
            size_bytes = int(file_info.get("size_bytes", 0))
            repo_size_bytes += size_bytes

            language = self.extension_classifier.detect_language(path)
            if not language:
                language = self.landmark_classifier.detect_language(path)
            if language:
                language_sizes[language] += size_bytes
                language_files[language] += 1
                continue

            file_kind = self.file_kind_classifier.detect_kind(path)
            if file_kind:
                file_kind_sizes[file_kind] += size_bytes
                file_kind_files[file_kind] += 1
                continue

            unknown_label = self.extension_classifier.unknown_extension_label(path) or "Unknown"
            unknown_sizes[unknown_label] += size_bytes
            unknown_files[unknown_label] += 1

        distribution = []
        for language, size_bytes in sorted(
            language_sizes.items(),
            key=lambda item: item[1],
            reverse=True,
        ):
            percentage = (size_bytes / repo_size_bytes * 100.0) if repo_size_bytes else 0.0
            distribution.append(
                {
                    "language": language,
                    "language_size_bytes": size_bytes,
                    "file_count": language_files[language],
                    "language_percentage": round(percentage, 2),
                }
            )

        file_kind_distribution = []
        for file_kind, size_bytes in sorted(
            file_kind_sizes.items(),
            key=lambda item: item[1],
            reverse=True,
        ):
            percentage = (size_bytes / repo_size_bytes * 100.0) if repo_size_bytes else 0.0
            file_kind_distribution.append(
                {
                    "file_kind": file_kind,
                    "file_kind_size_bytes": size_bytes,
                    "file_count": file_kind_files[file_kind],
                    "file_kind_percentage": round(percentage, 2),
                }
            )

        unknown_distribution = []
        for label, size_bytes in sorted(
            unknown_sizes.items(),
            key=lambda item: item[1],
            reverse=True,
        ):
            percentage = (size_bytes / repo_size_bytes * 100.0) if repo_size_bytes else 0.0
            unknown_distribution.append(
                {
                    "label": label,
                    "size_bytes": size_bytes,
                    "file_count": unknown_files[label],
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
            "primary_language": primary_language,
            "language_distribution": distribution,
            "file_kind_distribution": file_kind_distribution,
            "unknown_distribution": unknown_distribution,
            "errors": repo_payload.get("errors", []),
        }


def print_summary(results: List[Dict]) -> None:
    """Print global size-bytes summary across all repositories."""
    totals = defaultdict(int)
    file_kind_totals = defaultdict(int)
    unknown_totals = defaultdict(int)
    total_bytes = 0
    total_branches = 0

    for repo in results:
        total_bytes += int(repo.get("repo_size_bytes", 0))
        total_branches += int(repo.get("branch_count", 0))
        for lang_data in repo.get("language_distribution", []):
            language = lang_data["language"]
            totals[language] += int(lang_data.get("language_size_bytes", 0))
        for kind_data in repo.get("file_kind_distribution", []):
            file_kind = kind_data["file_kind"]
            file_kind_totals[file_kind] += int(kind_data.get("file_kind_size_bytes", 0))
        for unknown_data in repo.get("unknown_distribution", []):
            label = unknown_data["label"]
            unknown_totals[label] += int(unknown_data.get("size_bytes", 0))

    print("\nLanguage Summary (by bytes)")
    for language, size_bytes in sorted(totals.items(), key=lambda x: x[1], reverse=True):
        pct = (size_bytes / total_bytes * 100.0) if total_bytes else 0.0
        print(f"{language:24} {human_size(size_bytes):>10} {pct:6.2f}%")

    if file_kind_totals:
        print("\nNon-Language File Summary (by bytes)")
        for file_kind, size_bytes in sorted(
            file_kind_totals.items(),
            key=lambda x: x[1],
            reverse=True,
        ):
            pct = (size_bytes / total_bytes * 100.0) if total_bytes else 0.0
            print(f"{file_kind:24} {human_size(size_bytes):>10} {pct:6.2f}%")

    if unknown_totals:
        print("\nUnknown File Summary (by bytes)")
        for label, size_bytes in sorted(unknown_totals.items(), key=lambda x: x[1], reverse=True):
            pct = (size_bytes / total_bytes * 100.0) if total_bytes else 0.0
            print(f"{label:24} {human_size(size_bytes):>10} {pct:6.2f}%")

    print(f"\nTotal repos: {len(results)}")
    print(f"Total bytes: {human_size(total_bytes)}")
    print(f"Total branches discovered: {total_branches}")


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
