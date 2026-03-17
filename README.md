# Bitbucket Scanner (Server/Data Center)

## Technical Usage

For a full technical runbook (setup, workflow, threading, branch behavior, troubleshooting), see:

- `TECHNICAL_USAGE.txt`

This scanner is for **Bitbucket Server/Data Center only**.
It computes programming language distribution by **bytes** and also reports repository branches.

## What It Produces

For each repository:

- `repo_size_bytes`
- `repo_created_date_utc` (when available from Bitbucket)
- `primary_language` (largest programming language by bytes)
- `language_distribution` (programming languages only)
- `default_branch`
- `branch_count`
- `branches` (name, latest commit, is_default)

Example summary:

```text
payment-api
  Java      8.1 MB (primary programming language)

  default branch: main
  branches: 24
```

## Architecture and Roles

- `api/bitbucket_server.py`
Role: low-level Bitbucket API client.
Functionality:
- project/repo listing with pagination
- archive download via `/archive?format=zip`
- zip-entry size extraction via `ZipInfo.file_size`
- legacy fallback: file path listing via `/files`
- legacy fallback: file size by `HEAD /raw/{path}` using `Content-Length`
- branch listing + default branch discovery

- `collectors/repository_collector.py`
Role: raw data collection only.
Functionality:
- loops projects -> repos
- prefers one archive download per repo for file metadata
- falls back to recursive file listing + per-file HEAD requests when needed
- optionally collects branch metadata
- does **not** classify language

- `classifiers/extension_classifier.py`
Role: extension -> language mapping.
Functionality:
- loads GitHub Linguist `languages.yaml`
- matches exact filenames and extensions to language labels
- emits fallback labels for unknown extensions

- `classifiers/landmark_classifier.py`
Role: filename-based language hints.
Functionality:
- uses landmark files like `pom.xml`, `package.json`, `pyproject.toml`
- helps classify files without clear extensions

- `services/language_service.py`
Role: aggregation and metrics.
Functionality:
- groups bytes by programming language
- calculates percentages and file counts
- chooses primary language from programming languages only
- forwards branch metadata to final report

- `exporters/csv_exporter.py`
Role: tabular export.
Functionality:
- flattens nested JSON into rows (`repo x language`)
- includes branch fields (`default_branch`, `branch_count`, sample branch names)

- `exporters/json_exporter.py`
Role: full-fidelity export.
Functionality:
- writes complete nested structure for dashboards or pipelines

- `main.py`
Role: orchestration entrypoint.
Functionality:
- reads CLI + env config
- sets TLS behavior (insecure by default)
- runs collection -> aggregation -> export -> terminal summary

## API Facts Used by Scanner

1. Preferred repository scan:

`GET /projects/{project}/repos/{repo}/archive?format=zip`

- returns a zip archive for the selected repo/ref
- zip metadata already contains each file path and uncompressed file size

2. Legacy fallback file listing:

`GET /projects/{project}/repos/{repo}/files`

- returns paths only
- no file sizes in this response

3. Legacy fallback file size without downloading file body:

`HEAD /projects/{project}/repos/{repo}/raw/{file_path}`

- read header `Content-Length`

4. List branches:

`GET /projects/{project}/repos/{repo}/branches`

5. Get default branch:

`GET /projects/{project}/repos/{repo}/branches/default`

## Internal Network TLS Behavior

This project is configured for internal company networks:

- `BB_INSECURE=true` by default
- HTTPS certificate verification is disabled unless you explicitly set `BB_INSECURE=false`
- Optional custom CA bundle supported via `BB_CA_BUNDLE`

## Configuration

Environment variables:

- `BB_SERVER_URL` (required)
- `BB_SERVER_TOKEN` (required)
- `BB_INSECURE` (default: `true`)
- `BB_CA_BUNDLE` (optional when `BB_INSECURE=false`)
- `OUTPUT_CSV` (default: `bitbucket_languages.csv`)
- `OUTPUT_JSON` (default: `bitbucket_languages.json`)
- `MAX_WORKERS` (repo-level parallelism, default `8`)
- `FILE_WORKERS` (legacy per-repo fallback HEAD parallelism, default `16`)
- `INCLUDE_BRANCHES` (default `true`)
- `MAX_BRANCHES` (max branches stored per repo, default `100`, `0` = unlimited)

## CLI Usage

```bash
python main.py \
  --server-url "https://bitbucket.mycompany.com" \
  --server-token "<token>" \
  --max-workers 8 \
  --file-workers 16 \
  --include-branches \
  --max-branches 100
```

Options:

- `--no-parallel`: disable repo-level parallelism
- `--include-branches` / `--no-branches`: enable or disable branch collection
- `--max-branches N`: cap branch list stored in output (`0` means unlimited)

## Output Schemas

### JSON (nested)

Each repo object contains:

- `project_key`, `project_name`
- `repo_slug`, `repo_name`, `clone_url`
- `repo_created_date_raw`, `repo_created_date_utc`
- `default_branch`, `branch_count`, `branches_truncated`, `branches[]`
- `repo_size_bytes`, `primary_language`
- `language_distribution[]`
  - `language`
  - `language_size_bytes`
  - `file_count`
  - `language_percentage`
- `errors[]`

### CSV (flat)

One row per `repo x language`, plus branch metadata columns:

- `repo_created_date_raw`
- `repo_created_date_utc`
- `default_branch`
- `branch_count`
- `branches_truncated`
- `branch_sample` (first few branch names)

## Performance Notes

- Archive-first scanning usually needs 1 request per repo for file metadata.
- If archive download fails, the scanner falls back to 1 `HEAD` call per file.
- Branch collection adds more calls per repo.
- Tune `MAX_WORKERS` first; `FILE_WORKERS` only matters during fallback.
- Start conservative, then increase gradually while monitoring server load.
