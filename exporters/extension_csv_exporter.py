"""CSV exporter for flattened repository/extension scanner output."""

import csv


def save_extension_csv(results, path):
    if not results:
        print("No extension data to export")
        return

    rows = []
    for repo in results:
        branches = repo.get("branches", [])
        branch_sample = ", ".join(
            branch.get("name", "") for branch in branches[:10] if branch.get("name")
        )

        distribution = repo.get("extension_distribution", [])
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
                    "programming_size_bytes": repo.get("programming_size_bytes", 0),
                    "file_type_size_bytes": repo.get("file_type_size_bytes", 0),
                    "extension_size_bytes": repo.get("extension_size_bytes", 0),
                    "extension": "(none)",
                    "extension_size_repo_bytes": 0,
                    "extension_file_count": 0,
                    "extension_percentage": 0.0,
                }
            )
            continue

        for ext_data in distribution:
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
                    "programming_size_bytes": repo.get("programming_size_bytes", 0),
                    "file_type_size_bytes": repo.get("file_type_size_bytes", 0),
                    "extension_size_bytes": repo.get("extension_size_bytes", 0),
                    "extension": ext_data.get("extension", "(none)"),
                    "extension_size_repo_bytes": ext_data.get("size_bytes", 0),
                    "extension_file_count": ext_data.get("file_count", 0),
                    "extension_percentage": ext_data.get("percentage", 0.0),
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
        "programming_size_bytes",
        "file_type_size_bytes",
        "extension_size_bytes",
        "extension",
        "extension_size_repo_bytes",
        "extension_file_count",
        "extension_percentage",
    ]

    with open(path, "w", newline="", encoding="utf8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print("Extension CSV saved:", path)
