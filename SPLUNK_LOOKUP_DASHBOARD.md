# Splunk Lookup Dashboard Guide

## Scope

This guide assumes your Bitbucket scanner data is already stored in Splunk lookups.

Use this guide if you are building dashboards from:

- CSV lookups
- KV store lookups

and not from indexed events.

## Important Limitation

If your lookup is overwritten on every scan, then Splunk only has the latest snapshot.

That means:

- you can build current-state dashboards
- you cannot build trends over time
- you cannot calculate previous-vs-current differences reliably

To show differences over time, your lookup must keep history.

## Two Good Lookup Models

### 1. Current snapshot lookup

One lookup that contains only the latest data.

Good for:

- current biggest repositories
- current language distribution
- current branch counts
- current scan errors

Not enough for:

- size evolution over time
- delta from previous scan
- language growth over time

### 2. Historical lookup

Each scan appends new rows instead of replacing the old rows.

Each row should contain:

- `scan_time_utc`
- `repo_slug`
- `repo_name`
- `project_key`
- `repo_size_bytes`
- `primary_language`
- `branch_count`
- `language`
- `language_size_bytes`
- `file_count`
- `language_percentage`
- `errors`

This is the model you need for trends and diffs.

## Recommended Lookups

Best setup:

- `bitbucket_repo_summary`
- `bitbucket_repo_language`

### `bitbucket_repo_summary`

One row per repo per scan.

Suggested fields:

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

### `bitbucket_repo_language`

One row per repo-language per scan.

Suggested fields:

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

Do not calculate repository totals from the language lookup by summing `repo_size_bytes` if that field is repeated on each language row.

Use the repo-summary lookup for repo totals.

## Dashboard Panels Using `inputlookup`

### 1. Biggest Repositories Right Now

Use when the lookup contains only the current snapshot, or when you want the latest row from a historical lookup.

If the lookup is current-only:

```spl
| inputlookup bitbucket_repo_summary
| sort - repo_size_bytes
| table repo_slug repo_name repo_size_bytes primary_language branch_count
```

If the lookup is historical:

```spl
| inputlookup bitbucket_repo_summary
| eval _time=strptime(scan_time_utc,"%Y-%m-%dT%H:%M:%SZ")
| sort 0 repo_slug - _time
| dedup repo_slug
| sort - repo_size_bytes
| table repo_slug repo_name repo_size_bytes primary_language branch_count
```

### 2. Current Language Distribution

Current-only lookup:

```spl
| inputlookup bitbucket_repo_language
| stats sum(language_size_bytes) as language_size_bytes by language
| sort - language_size_bytes
```

Historical lookup, latest snapshot only:

```spl
| inputlookup bitbucket_repo_language
| eval _time=strptime(scan_time_utc,"%Y-%m-%dT%H:%M:%SZ")
| eventstats max(_time) as latest_time
| where _time=latest_time
| stats sum(language_size_bytes) as language_size_bytes by language
| sort - language_size_bytes
```

### 3. Current Branch Counts

```spl
| inputlookup bitbucket_repo_summary
| sort - branch_count
| table repo_slug repo_name branch_count default_branch
```

### 4. Repositories With Errors

```spl
| inputlookup bitbucket_repo_summary
| where errors!="" AND errors!="[]"
| table scan_time_utc repo_slug repo_name errors
```

## Panels That Need Historical Lookups

These do not work correctly if the lookup is overwritten each run.

### 5. Repo Size Delta Between Scans

```spl
| inputlookup bitbucket_repo_summary
| eval _time=strptime(scan_time_utc,"%Y-%m-%dT%H:%M:%SZ")
| sort 0 repo_slug _time
| streamstats current=f last(repo_size_bytes) as prev_size by repo_slug
| eval size_delta=repo_size_bytes-prev_size
| where isnotnull(prev_size)
| sort - size_delta
| table scan_time_utc repo_slug repo_name prev_size repo_size_bytes size_delta
```

### 6. Repository Size Trend

```spl
| inputlookup bitbucket_repo_summary
| eval _time=strptime(scan_time_utc,"%Y-%m-%dT%H:%M:%SZ")
| timechart span=1d latest(repo_size_bytes) by repo_slug
```

### 7. Language Growth Over Time

```spl
| inputlookup bitbucket_repo_language
| eval _time=strptime(scan_time_utc,"%Y-%m-%dT%H:%M:%SZ")
| timechart span=1d sum(language_size_bytes) by language
```

## If You Have Only One Lookup

If your lookup is the current `repo x language` CSV shape only, then you can still build a basic dashboard.

### Biggest languages right now

```spl
| inputlookup bitbucket_languages
| stats sum(language_size_bytes) as language_size_bytes by language
| sort - language_size_bytes
```

### Current repo/language table

```spl
| inputlookup bitbucket_languages
| table project_key repo_slug repo_name language language_size_bytes file_count language_percentage primary_language repo_size_bytes
```

### Current biggest repositories

Because repo size is repeated once per language row, deduplicate first:

```spl
| inputlookup bitbucket_languages
| dedup repo_slug
| sort - repo_size_bytes
| table repo_slug repo_name repo_size_bytes primary_language branch_count
```

## Best Dashboard Layout For Lookup Data

If you only have current snapshot data:

Top row:

- biggest repositories
- repositories with errors

Middle row:

- current language distribution
- current branch counts

Bottom row:

- repo/language detail table

If you have historical lookup data:

Top row:

- biggest repositories
- repo size delta between scans

Middle row:

- repository size trend
- language growth over time

Bottom row:

- current language distribution
- repositories with errors

## When You Need To Change The Scanner

You only need scanner changes if you want trend dashboards or deltas.

Minimum scanner/export changes for that:

1. Add `scan_time_utc` to each row.
2. Append rows to a history lookup instead of replacing one lookup.
3. Prefer a separate repo-summary lookup for repo totals.

Without those changes, your dashboard can only show the latest snapshot.
