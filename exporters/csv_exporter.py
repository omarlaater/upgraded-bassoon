"""CSV exporter for a single unified repository inventory output."""

import csv


def save_csv(results, path):
    if not results:
        print("No data to export")
        return

    rows = []
    for repo in results:
        branches = repo.get("branches", [])
        branch_sample = ", ".join(
            branch.get("name", "") for branch in branches[:10] if branch.get("name")
        )
        errors = repo.get("errors", [])
        errors_text = "; ".join(str(error) for error in errors) if errors else ""

        base_row = {
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
            "unmapped_extension_size_bytes": repo.get("unmapped_extension_size_bytes", 0),
            "errors": errors_text,
        }

        rows.append(
            {
                **base_row,
                "row_type": "repo_summary",
                "item_name": "",
                "item_category": "",
                "eligible_for_primary": "",
                "size_bytes": "",
                "file_count": "",
                "percentage": "",
                "percentage_basis": "",
            }
        )

        for language_data in repo.get("language_distribution", []):
            rows.append(
                {
                    **base_row,
                    "row_type": "programming_language",
                    "item_name": language_data.get("language", "Unknown"),
                    "item_category": "programming",
                    "eligible_for_primary": True,
                    "size_bytes": language_data.get("language_size_bytes", 0),
                    "file_count": language_data.get("file_count", 0),
                    "percentage": language_data.get("language_percentage", 0.0),
                    "percentage_basis": "programming_size_bytes",
                }
            )

        for file_type_data in repo.get("file_type_distribution", []):
            rows.append(
                {
                    **base_row,
                    "row_type": "file_type",
                    "item_name": file_type_data.get("language", ""),
                    "item_category": file_type_data.get("type", ""),
                    "eligible_for_primary": file_type_data.get("eligible_for_primary", False),
                    "size_bytes": file_type_data.get("size_bytes", 0),
                    "file_count": file_type_data.get("file_count", 0),
                    "percentage": file_type_data.get("percentage", 0.0),
                    "percentage_basis": "file_type_size_bytes",
                }
            )

        for ext_data in repo.get("unmapped_extension_distribution", []):
            rows.append(
                {
                    **base_row,
                    "row_type": "unmapped_extension",
                    "item_name": ext_data.get("extension", ""),
                    "item_category": "unmapped_extension",
                    "eligible_for_primary": False,
                    "size_bytes": ext_data.get("size_bytes", 0),
                    "file_count": ext_data.get("file_count", 0),
                    "percentage": ext_data.get("percentage", 0.0),
                    "percentage_basis": "unmapped_extension_size_bytes",
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
        "unmapped_extension_size_bytes",
        "row_type",
        "item_name",
        "item_category",
        "eligible_for_primary",
        "size_bytes",
        "file_count",
        "percentage",
        "percentage_basis",
        "errors",
    ]

    with open(path, "w", newline="", encoding="utf8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print("CSV saved:", path)
