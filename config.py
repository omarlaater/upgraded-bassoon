import os

# Bitbucket Server / Data Center connection
SERVER_URL = os.getenv("BB_SERVER_URL", "https://bitbucket.mycompany.com")
SERVER_TOKEN = os.getenv("BB_SERVER_TOKEN", "")

CA_BUNDLE = os.getenv("BB_CA_BUNDLE", "")
# In internal networks this defaults to insecure TLS unless explicitly disabled.
INSECURE = os.getenv("BB_INSECURE", "true").strip().lower() in {"1", "true", "yes", "on"}

# Output files
OUTPUT_CSV = os.getenv("OUTPUT_CSV", "bitbucket_languages.csv")
OUTPUT_JSON = os.getenv("OUTPUT_JSON", "bitbucket_languages.json")
OUTPUT_EXTENSIONS_CSV = os.getenv(
    "OUTPUT_EXTENSIONS_CSV",
    "bitbucket_unmapped_extensions.csv",
)

# Concurrency
DEFAULT_MAX_WORKERS = int(os.getenv("MAX_WORKERS", "8"))
# Legacy per-repository concurrency for HEAD /raw/{path} fallback requests.
# Archive-first scans do not need this, but we keep the setting so the older
# code path still works when the archive endpoint is unavailable.
DEFAULT_FILE_WORKERS = int(os.getenv("FILE_WORKERS", "16"))

# Branch metadata collection
INCLUDE_BRANCHES = os.getenv("INCLUDE_BRANCHES", "true").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
DEFAULT_MAX_BRANCHES = int(os.getenv("MAX_BRANCHES", "100"))
