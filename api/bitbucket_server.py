"""Bitbucket Server/Data Center REST client used by scanner layers."""

import tempfile
import zipfile
from typing import Dict, Iterator, List
from urllib.parse import quote

from api.session import make_session
from utils.url import normalize_server_url


class BitbucketServerScraper:
    """API client for Bitbucket Server/Data Center endpoints used by the scanner."""

    # We ask Bitbucket to place every archive entry under a stable root folder.
    # That makes it easy to strip the synthetic archive prefix and recover the
    # original repository-relative path expected by the rest of the scanner.
    ARCHIVE_PREFIX = "__scanner_archive_root__"

    def __init__(self, base_url: str, token: str, verify: bool = True):
        if not token:
            raise ValueError("Bitbucket token is required")

        normalized = normalize_server_url(base_url)
        self.base = normalized.rstrip("/") + "/rest/api/1.0"
        # The archive endpoint is documented under `latest`; keeping both bases
        # lets us add the new strategy without disturbing existing calls.
        self.latest_base = normalized.rstrip("/") + "/rest/api/latest"
        self.session = make_session(verify)
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    def _paginate(self, url: str, params: Dict | None = None) -> Iterator[Dict]:
        """Yield all objects from paginated Bitbucket APIs."""
        params = params or {}
        params.setdefault("limit", 100)
        start = 0

        while True:
            params["start"] = start
            response = self.session.get(
                url,
                headers=self.headers,
                params=params,
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()

            for value in data.get("values", []):
                yield value

            if data.get("isLastPage", True):
                break

            start = data.get("nextPageStart", start + params["limit"])

    def get_projects(self) -> List[Dict]:
        """Return all projects visible to the token."""
        return list(self._paginate(f"{self.base}/projects"))

    def get_repos(self, project_key: str) -> List[Dict]:
        """Return all repositories in a project."""
        return list(self._paginate(f"{self.base}/projects/{project_key}/repos"))

    def get_files(self, project_key: str, repo_slug: str, at: str = "") -> List[str]:
        """Return all file paths in a repository (recursive)."""
        url = f"{self.base}/projects/{project_key}/repos/{repo_slug}/files"
        params: Dict[str, str] = {}
        if at:
            params["at"] = at
        return list(self._paginate(url, params=params))

    def get_branches(
        self,
        project_key: str,
        repo_slug: str,
        max_branches: int | None = None,
    ) -> List[Dict]:
        """
        Return repository branches.
        `max_branches` bounds payload size when repos contain many branches.
        """
        url = f"{self.base}/projects/{project_key}/repos/{repo_slug}/branches"
        branches: List[Dict] = []
        for branch in self._paginate(url):
            branches.append(branch)
            if max_branches and len(branches) >= max_branches:
                break
        return branches

    def get_default_branch(self, project_key: str, repo_slug: str) -> str:
        """Return default branch display name when available."""
        url = (
            f"{self.base}/projects/{project_key}/repos/"
            f"{repo_slug}/branches/default"
        )
        response = self.session.get(url, headers=self.headers, timeout=30)
        if response.status_code == 404:
            return ""
        response.raise_for_status()
        payload = response.json()
        return payload.get("displayId") or payload.get("id") or ""

    def get_file_size(
        self,
        project_key: str,
        repo_slug: str,
        file_path: str,
        at: str = "",
    ) -> int:
        """
        Read file size from HEAD /raw/{path} without downloading file content.
        Returns 0 when Content-Length is missing or invalid.
        """
        encoded_path = quote(file_path, safe="/")
        url = f"{self.base}/projects/{project_key}/repos/{repo_slug}/raw/{encoded_path}"
        params: Dict[str, str] = {}
        if at:
            params["at"] = at
        response = self.session.head(
            url,
            headers=self.headers,
            params=params,
            timeout=30,
        )
        response.raise_for_status()

        raw_size = response.headers.get("Content-Length") or response.headers.get(
            "content-length"
        )
        if not raw_size:
            return 0

        try:
            return int(raw_size)
        except (TypeError, ValueError):
            return 0

    def get_archive_file_sizes(
        self,
        project_key: str,
        repo_slug: str,
        at: str = "",
        paths: List[str] | None = None,
    ) -> List[Dict]:
        """
        Download a single zip archive and read file sizes from zip entry metadata.

        This keeps the downstream payload identical to the old per-file strategy:
        each item is still `{"path": "...", "size_bytes": N}`.
        """
        url = f"{self.latest_base}/projects/{project_key}/repos/{repo_slug}/archive"

        # `prefix` gives us deterministic entry names inside the archive, which
        # avoids depending on Bitbucket's generated top-level folder naming.
        params: List[tuple[str, str]] = [
            ("format", "zip"),
            ("prefix", self.ARCHIVE_PREFIX),
        ]
        if at:
            params.append(("at", at))
        for path in paths or []:
            params.append(("path", path))

        with self.session.get(
            url,
            headers=self.headers,
            params=params,
            timeout=(30, 300),
            stream=True,
        ) as response:
            response.raise_for_status()

            # TemporaryFile keeps archive handling compatible with large
            # repositories without holding the entire zip in memory.
            with tempfile.TemporaryFile() as archive_buffer:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        archive_buffer.write(chunk)

                archive_buffer.seek(0)

                with zipfile.ZipFile(archive_buffer) as archive_file:
                    files: List[Dict] = []
                    for info in archive_file.infolist():
                        if info.is_dir():
                            continue

                        path = self._normalize_archive_member_path(info.filename)
                        if not path:
                            continue

                        files.append(
                            {
                                "path": path,
                                "size_bytes": int(info.file_size),
                            }
                        )

        return files

    def _normalize_archive_member_path(self, member_name: str) -> str:
        """
        Convert a raw zip entry name into the repository-relative path expected by
        the collector and classifiers.
        """
        normalized = member_name.replace("\\", "/").strip("/")
        if not normalized:
            return ""

        prefix = self.ARCHIVE_PREFIX.rstrip("/")
        if normalized == prefix:
            return ""

        if normalized.startswith(f"{prefix}/"):
            return normalized[len(prefix) + 1 :]

        # Fallback for unexpected server behaviour: keep the original member path
        # rather than failing the entire scan.
        return normalized
