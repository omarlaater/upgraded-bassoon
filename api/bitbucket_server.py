"""Bitbucket Server/Data Center REST client used by scanner layers."""

from typing import Dict, Iterator, List
from urllib.parse import quote

from api.session import make_session
from utils.url import normalize_server_url


class BitbucketServerScraper:
    """API client for Bitbucket Server/Data Center endpoints used by the scanner."""

    def __init__(self, base_url: str, token: str, verify: bool = True):
        if not token:
            raise ValueError("Bitbucket token is required")

        normalized = normalize_server_url(base_url)
        self.base = normalized.rstrip("/") + "/rest/api/1.0"
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

    def get_files(self, project_key: str, repo_slug: str) -> List[str]:
        """Return all file paths in a repository (recursive)."""
        url = f"{self.base}/projects/{project_key}/repos/{repo_slug}/files"
        return list(self._paginate(url))

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

    def get_file_size(self, project_key: str, repo_slug: str, file_path: str) -> int:
        """
        Read file size from HEAD /raw/{path} without downloading file content.
        Returns 0 when Content-Length is missing or invalid.
        """
        encoded_path = quote(file_path, safe="/")
        url = f"{self.base}/projects/{project_key}/repos/{repo_slug}/raw/{encoded_path}"
        response = self.session.head(url, headers=self.headers, timeout=30)
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
