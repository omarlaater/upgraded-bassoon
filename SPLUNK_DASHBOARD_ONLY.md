# Splunk Dashboard Only Guide

## Scope

This file is only about building dashboards in Splunk later.

It does not cover:

- sending data to Splunk
- HEC
- Universal Forwarder
- scheduling the scanner
- Windows Task Scheduler

Assumption:

- scanner data is already indexed in Splunk

## Recommended Data Model

Build dashboards from two event types:

### 1. Repo summary events

Use these fields:

- `scan_time_utc`
- `project_key`
- `project_name`
- `repo_slug`
- `repo_name`
- `default_branch`
- `branch_count`
- `repo_size_bytes`
- `primary_language`
- `errors`

### 2. Repo language events

Use these fields:

- `scan_time_utc`
- `project_key`
- `project_name`
- `repo_slug`
- `repo_name`
- `language`
- `language_size_bytes`
- `file_count`
- `language_percentage`

## Important Rule

Do not calculate total repository size from `repo x language` rows by summing `repo_size_bytes`.

Why:

- the same repo size is repeated once per language row

Use repo summary events for repo totals.

## Suggested Sourcetypes

Examples:

- `bitbucket:repo_summary_csv`
- `bitbucket:repo_language_csv`

Example index:

- `bitbucket_scanner`

## Dashboard Panels To Build

Start with these panels.

### 1. Biggest Repositories

Purpose:

- show the latest size of each repo

```spl
index=bitbucket_scanner sourcetype=bitbucket:repo_summary_csv
| stats latest(repo_size_bytes) as repo_size_bytes latest(primary_language) as primary_language by repo_slug repo_name
| sort - repo_size_bytes
```

Visualization:

- table

Suggested columns:

- `repo_slug`
- `repo_name`
- `repo_size_bytes`
- `primary_language`

### 2. Repository Size Over Time

Purpose:

- show growth for selected repos

```spl
index=bitbucket_scanner sourcetype=bitbucket:repo_summary_csv
| timechart span=1d latest(repo_size_bytes) by repo_slug
```

Visualization:

- line chart

Tip:

- add an input filter for `repo_slug`

### 3. Repo Growth Since Previous Scan

Purpose:

- show which repos changed most between scans

```spl
index=bitbucket_scanner sourcetype=bitbucket:repo_summary_csv
| sort 0 repo_slug _time
| streamstats current=f last(repo_size_bytes) as prev_size by repo_slug
| eval size_delta=repo_size_bytes-prev_size
| where isnotnull(prev_size)
| sort - size_delta
```

Visualization:

- table

Suggested columns:

- `repo_slug`
- `repo_size_bytes`
- `prev_size`
- `size_delta`

### 4. Language Distribution By Bytes

Purpose:

- show current language mix across all repositories

```spl
index=bitbucket_scanner sourcetype=bitbucket:repo_language_csv
| stats sum(language_size_bytes) as language_size_bytes by language
| sort - language_size_bytes
```

Visualization:

- bar chart

### 5. Language Trend Over Time

Purpose:

- show whether Java, Python, JavaScript, etc. are growing or shrinking

```spl
index=bitbucket_scanner sourcetype=bitbucket:repo_language_csv
| timechart span=1d sum(language_size_bytes) by language
```

Visualization:

- stacked area chart
- line chart

### 6. Primary Language By Repository

Purpose:

- show the current dominant language of each repo

```spl
index=bitbucket_scanner sourcetype=bitbucket:repo_summary_csv
| stats latest(primary_language) as primary_language latest(repo_size_bytes) as repo_size_bytes by repo_slug
| sort repo_slug
```

Visualization:

- table

### 7. Branch Count By Repository

Purpose:

- monitor repos with many branches

```spl
index=bitbucket_scanner sourcetype=bitbucket:repo_summary_csv
| stats latest(branch_count) as branch_count by repo_slug
| sort - branch_count
```

Visualization:

- table
- bar chart

### 8. Scan Errors

Purpose:

- show repos that failed or partially failed during scans

```spl
index=bitbucket_scanner sourcetype=bitbucket:repo_summary_csv
| where errors!="" AND errors!="[]"
| table _time repo_slug repo_name errors
| sort - _time
```

Visualization:

- table

## Filters To Add On The Dashboard

Useful dashboard inputs:

- time range
- `project_key`
- `repo_slug`
- `primary_language`

These filters let one dashboard serve both global and repo-specific views.

## Good First Dashboard Layout

Top row:

- biggest repositories
- repos with scan errors

Middle row:

- repository size over time
- repo growth since previous scan

Bottom row:

- language distribution by bytes
- language trend over time

## Alerts To Add Later

Once the dashboard is stable, useful alerts are:

- repo size increased by more than X% since previous scan
- primary language changed for a repo
- branch count jumped above a threshold
- scan errors appeared for a repo

## Minimum Fields Needed For Good Dashboards

If you want the dashboard to work well later, make sure the data in Splunk includes:

- `_time` or `scan_time_utc`
- `repo_slug`
- `repo_name`
- `repo_size_bytes`
- `primary_language`
- `branch_count`
- `language`
- `language_size_bytes`
- `file_count`
- `errors`

## Practical Advice

If you only build one event type, choose repo summary first.

Why:

- repo size trends are the most useful first dashboard
- growth alerts are easier
- no duplicate repo-size rows problem

If you later add repo language events, then you can build the language charts cleanly.
