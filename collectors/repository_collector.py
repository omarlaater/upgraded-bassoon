"""Collector layer: gathers raw repository/files/branch metadata from API layer."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Tuple

from config import (
    DEFAULT_FILE_WORKERS,
    DEFAULT_MAX_BRANCHES,
    DEFAULT_MAX_WORKERS,
    INCLUDE_BRANCHES,
)
from utils.datetime_utils import to_utc_iso


IGNORE_DIRS = {
    "node_modules",
    "vendor",
    "dist",
    "build",
    "target",
    "__pycache__",
    ".git",
    ".idea",
    ".vscode",
    "venv",
    ".venv",
    "env",
}


class RepositoryCollector:
    """
    Collects raw repository data only.
    No language logic is applied here; output is file metadata + file sizes.
    """

    def __init__(self, scraper):
        self.scraper = scraper

    def collect(
        self,
        parallel: bool = True,
        max_workers: int = DEFAULT_MAX_WORKERS,
        file_workers: int = DEFAULT_FILE_WORKERS,
        include_branches: bool = INCLUDE_BRANCHES,
        max_branches: int = DEFAULT_MAX_BRANCHES,
    ) -> List[Dict]:
        projects = self.scraper.get_projects()
        print(f"Found {len(projects)} projects")

        tasks: List[Tuple[str, str, Dict]] = []
        for project in projects:
            project_key = project["key"]
            project_name = project.get("name", project_key)
            repos = self.scraper.get_repos(project_key)
            print(f"Project {project_name}: {len(repos)} repositories")
            tasks.extend((project_key, project_name, repo) for repo in repos)

        if not tasks:
            return []

        if not parallel:
            return [
                self._collect_repo(task, file_workers, include_branches, max_branches)
                for task in tasks
            ]

        results: List[Dict] = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    self._collect_repo,
                    task,
                    file_workers,
                    include_branches,
                    max_branches,
                ): task
                for task in tasks
            }
            for future in as_completed(futures):
                results.append(future.result())

        return results

    def _collect_repo(
        self,
        task: Tuple[str, str, Dict],
        file_workers: int,
        include_branches: bool,
        max_branches: int,
    ) -> Dict:
        project_key, project_name, repo = task
        repo_slug = repo["slug"]
        repo_name = repo.get("name", repo_slug)
        clone_url = self._extract_clone_url(repo)
        repo_created_date_raw = repo.get("createdDate", "")
        repo_created_date_utc = to_utc_iso(repo_created_date_raw)
        errors: List[str] = []

        branches: List[Dict] = []
        default_branch = ""
        branches_truncated = False
        if include_branches:
            branches, default_branch, branches_truncated, branch_error = self._collect_branches(
                project_key=project_key,
                repo_slug=repo_slug,
                max_branches=max_branches,
            )
            if branch_error:
                errors.append(branch_error)

        try:
            # When branch metadata is available, reuse that ref for the file scan.
            # This keeps archive extraction and legacy API fallback aligned to the
            # same branch instead of whatever Bitbucket considers "current" later.
            scan_ref = default_branch or ""
            files, scan_strategy = self._collect_repo_files(
                project_key=project_key,
                repo_slug=repo_slug,
                scan_ref=scan_ref,
                file_workers=file_workers,
                errors=errors,
            )
        except Exception as exc:
            print(f"error collecting files for {repo_slug}: {exc}")
            return {
                "project_key": project_key,
                "project_name": project_name,
                "repo_slug": repo_slug,
                "repo_name": repo_name,
                "clone_url": clone_url,
                "repo_created_date_raw": repo_created_date_raw,
                "repo_created_date_utc": repo_created_date_utc,
                "files": [],
                "default_branch": default_branch,
                "branch_count": len(branches),
                "branches_truncated": branches_truncated,
                "branches": branches,
                "errors": errors + [f"file_collection_failed: {exc}"],
            }

        print(
            f"{repo_name:40} files={len(files):5} "
            f"strategy={scan_strategy:8} "
            f"branches={len(branches):4}"
        )

        return {
            "project_key": project_key,
            "project_name": project_name,
            "repo_slug": repo_slug,
            "repo_name": repo_name,
            "clone_url": clone_url,
            "repo_created_date_raw": repo_created_date_raw,
            "repo_created_date_utc": repo_created_date_utc,
            "files": files,
            "default_branch": default_branch,
            "branch_count": len(branches),
            "branches_truncated": branches_truncated,
            "branches": branches,
            "errors": errors,
        }

    def _collect_branches(
        self,
        project_key: str,
        repo_slug: str,
        max_branches: int,
    ) -> Tuple[List[Dict], str, bool, str | None]:
        """
        Collect lightweight branch metadata for reporting.
        Returns branches, default_branch, truncated, optional_error.
        """
        try:
            # Ask one extra branch so we can detect truncation accurately.
            query_limit = (max_branches + 1) if max_branches else None
            raw_branches = self.scraper.get_branches(
                project_key=project_key,
                repo_slug=repo_slug,
                max_branches=query_limit,
            )
            default_branch = self.scraper.get_default_branch(project_key, repo_slug)
        except Exception as exc:
            return [], "", False, f"branch_collection_failed: {exc}"

        truncated = False
        if max_branches and len(raw_branches) > max_branches:
            truncated = True
            raw_branches = raw_branches[:max_branches]

        branches = [
            {
                "name": branch.get("displayId") or branch.get("id") or "",
                "latest_commit": branch.get("latestCommit", ""),
                "is_default": (branch.get("displayId") or branch.get("id") or "")
                == default_branch,
            }
            for branch in raw_branches
        ]
        return branches, default_branch, truncated, None

    def _collect_repo_files(
        self,
        project_key: str,
        repo_slug: str,
        scan_ref: str,
        file_workers: int,
        errors: List[str],
    ) -> Tuple[List[Dict], str]:
        """
        Prefer the single-archive workflow for speed, then fall back to the
        legacy `/files` + `HEAD /raw` path if the server cannot provide it.
        """
        try:
            files = self.scraper.get_archive_file_sizes(
                project_key=project_key,
                repo_slug=repo_slug,
                at=scan_ref,
            )
            filtered_files = [
                file_info for file_info in files if not self._is_ignored(file_info["path"])
            ]
            return filtered_files, "archive"
        except Exception as exc:
            # Keep the failure visible in the exported output, but do not stop the
            # scan when the older path-based strategy can still succeed.
            errors.append(f"archive_scan_failed_fallback_used: {exc}")
            print(
                f"archive scan failed for {repo_slug}: {exc}; "
                "falling back to /files + HEAD"
            )

        file_paths = self.scraper.get_files(project_key, repo_slug, at=scan_ref)
        filtered_paths = [path for path in file_paths if not self._is_ignored(path)]
        files = self._collect_file_sizes(
            project_key=project_key,
            repo_slug=repo_slug,
            file_paths=filtered_paths,
            file_workers=file_workers,
            at=scan_ref,
        )
        return files, "fallback"

    def _collect_file_sizes(
        self,
        project_key: str,
        repo_slug: str,
        file_paths: List[str],
        file_workers: int,
        at: str = "",
    ) -> List[Dict]:
        if not file_paths:
            return []

        def one(path: str) -> Dict:
            try:
                size = self.scraper.get_file_size(
                    project_key,
                    repo_slug,
                    path,
                    at=at,
                )
                return {"path": path, "size_bytes": size}
            except Exception:
                # Keep failures explicit as zero-sized entries so aggregation remains stable.
                return {"path": path, "size_bytes": 0}

        if file_workers <= 1:
            return [one(path) for path in file_paths]

        files: List[Dict] = []
        with ThreadPoolExecutor(max_workers=file_workers) as executor:
            futures = {executor.submit(one, path): path for path in file_paths}
            for future in as_completed(futures):
                files.append(future.result())
        return files

    @staticmethod
    def _extract_clone_url(repo: Dict) -> str:
        for link in repo.get("links", {}).get("clone", []):
            if link.get("name") in ("http", "https"):
                return link.get("href", "")
        return ""

    @staticmethod
    def _is_ignored(path: str) -> bool:
        parts = [part.lower() for part in path.split("/")]
        return any(part in IGNORE_DIRS for part in parts)
