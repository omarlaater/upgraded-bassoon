"""CSV exporter for flattened repository/language scanner output."""

import csv


def save_csv(results, path):
    if not results:
        print("No data to export")
        return

    # Flatten nested `language_distribution` so each CSV row is repo x language.
    rows = []
    for repo in results:
        branches = repo.get("branches", [])
        # Keep CSV compact: include branch count + a short sample list.
        branch_sample = ", ".join(
            branch.get("name", "") for branch in branches[:10] if branch.get("name")
        )

        distribution = repo.get("language_distribution", [])
        if not distribution:
            rows.append(
                {
                    "project_key": repo.get("project_key", ""),
                    "project_name": repo.get("project_name", ""),
                    "repo_slug": repo.get("repo_slug", ""),
                    "repo_name": repo.get("repo_name", ""),
                    "clone_url": repo.get("clone_url", ""),
                    "repo_created_date_raw": repo.get("repo_created_date_raw", ""),
                    "repo_created_date_utc": repo.get("repo_created_date_utc", ""),
                    "default_branch": repo.get("default_branch", ""),
                    "branch_count": repo.get("branch_count", 0),
                    "branches_truncated": repo.get("branches_truncated", False),
                    "branch_sample": branch_sample,
                    "primary_language": repo.get("primary_language", "Unknown"),
                    "repo_size_bytes": repo.get("repo_size_bytes", 0),
                    "language": "Unknown",
                    "language_size_bytes": 0,
                    "file_count": 0,
                    "language_percentage": 0.0,
                }
            )
            continue

        for language_data in distribution:
            rows.append(
                {
                    "project_key": repo.get("project_key", ""),
                    "project_name": repo.get("project_name", ""),
                    "repo_slug": repo.get("repo_slug", ""),
                    "repo_name": repo.get("repo_name", ""),
                    "clone_url": repo.get("clone_url", ""),
                    "repo_created_date_raw": repo.get("repo_created_date_raw", ""),
                    "repo_created_date_utc": repo.get("repo_created_date_utc", ""),
                    "default_branch": repo.get("default_branch", ""),
                    "branch_count": repo.get("branch_count", 0),
                    "branches_truncated": repo.get("branches_truncated", False),
                    "branch_sample": branch_sample,
                    "primary_language": repo.get("primary_language", "Unknown"),
                    "repo_size_bytes": repo.get("repo_size_bytes", 0),
                    "language": language_data.get("language", "Unknown"),
                    "language_size_bytes": language_data.get("language_size_bytes", 0),
                    "file_count": language_data.get("file_count", 0),
                    "language_percentage": language_data.get("language_percentage", 0.0),
                }
            )

    fieldnames = [
        "project_key",
        "project_name",
        "repo_slug",
        "repo_name",
        "clone_url",
        "repo_created_date_raw",
        "repo_created_date_utc",
        "default_branch",
        "branch_count",
        "branches_truncated",
        "branch_sample",
        "primary_language",
        "repo_size_bytes",
        "language",
        "language_size_bytes",
        "file_count",
        "language_percentage",
    ]

    with open(path, "w", newline="", encoding="utf8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print("CSV saved:", path)
