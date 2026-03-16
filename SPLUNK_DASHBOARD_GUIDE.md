# Splunk Dashboard Guide

## What Changed Already

These files were changed in the scanner:

- `api/bitbucket_server.py`
- `collectors/repository_collector.py`
- `main.py`
- `config.py`
- `README.md`
- `TECHNICAL_USAGE.txt`

## Exact Functional Changes

### 1. File sizing strategy changed

Before:

- list files with `/files`
- get size per file with `HEAD /raw/{path}`
- if `Content-Length` was missing, that file became `0`

Now:

- try one repo archive download with `/archive?format=zip`
- open the zip locally
- read each file size from `ZipInfo.file_size`
- if archive fails, fall back to the old `/files` + `HEAD /raw` logic

### 2. Output contract stayed the same

The rest of the project still receives file items in this format:

```python
{"path": "src/app.py", "size_bytes": 4200}
```

That means the language service and exporters still work without structural changes.

### 3. Branch-aware scanning was tightened

When a default branch is known, the collector now reuses that ref during file scanning so archive/fallback calls stay on the same branch.

## What Was NOT Changed

No Splunk-specific code was added yet.

That means:

- no Splunk API integration
- no HEC sender
- no dashboard JSON
- no scheduled task script
- no timestamped historical export files
- no `scan_time_utc` field in the CSV rows
- no separate `repo_summary` export yet

## Why This Matters For Splunk

The current CSV exporter is usable for Splunk ingestion, but it is not ideal for history and dashboards yet because:

- it overwrites the same file each run
- it does not include scan timestamp metadata per row
- `repo_size_bytes` is repeated on every `repo x language` row

## What Should Be Added Next For Splunk

Recommended next changes:

1. Add `scan_time_utc` to every exported row.
2. Write one new output file per run instead of overwriting one file.
3. Add a second flat export with one row per repository:
   - `repo_slug`
   - `repo_name`
   - `project_key`
   - `default_branch`
   - `branch_count`
   - `repo_size_bytes`
   - `primary_language`
   - `errors`
   - `scan_time_utc`
4. Keep the existing language CSV for:
   - `language`
   - `language_size_bytes`
   - `file_count`
   - `language_percentage`
5. Let Splunk monitor the export folder.

## Recommended Splunk Model

Use two sourcetypes:

### `bitbucket:repo_summary_csv`

One row per repo per scan.

Use it for:

- repo size trend
- repo growth delta
- branch count changes
- primary language changes
- scan errors

### `bitbucket:repo_language_csv`

One row per repo-language per scan.

Use it for:

- language distribution
- language growth over time
- biggest languages across all repos

## Important Note

Do not build total repository-size dashboards from the current language CSV alone by summing `repo_size_bytes`, because that value is repeated for every language row of the same repo.

Use a dedicated repo-summary export for repo totals.

## Simple Next Step

If you want this project to be Splunk-ready, the next implementation step should be:

- add `scan_time_utc`
- add timestamped output filenames
- add `repo_summary` CSV export
- keep current language CSV export

After that, Splunk can monitor the folder and build dashboards cleanly.
