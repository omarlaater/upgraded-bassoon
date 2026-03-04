"""CLI entrypoint: orchestrates collection, aggregation, and exports."""

import argparse
import requests

from api.bitbucket_server import BitbucketServerScraper
from collectors.repository_collector import RepositoryCollector
from classifiers.extension_classifier import ExtensionClassifier
from classifiers.landmark_classifier import LandmarkClassifier
from exporters.csv_exporter import save_csv
from exporters.json_exporter import save_json
from services.language_service import LanguageService, print_summary

import config


def main():
    parser = argparse.ArgumentParser(
        description="Scan Bitbucket repositories and compute language distribution by bytes."
    )
    parser.add_argument("--server-url", default=config.SERVER_URL)
    parser.add_argument("--server-token", default=config.SERVER_TOKEN)
    parser.add_argument("--out-csv", default=config.OUTPUT_CSV)
    parser.add_argument("--out-json", default=config.OUTPUT_JSON)
    parser.add_argument("--max-workers", type=int, default=config.DEFAULT_MAX_WORKERS)
    parser.add_argument("--file-workers", type=int, default=config.DEFAULT_FILE_WORKERS)
    parser.add_argument("--max-branches", type=int, default=config.DEFAULT_MAX_BRANCHES)
    parser.add_argument("--include-branches", dest="include_branches", action="store_true")
    parser.add_argument("--no-branches", dest="include_branches", action="store_false")
    parser.set_defaults(include_branches=config.INCLUDE_BRANCHES)
    parser.add_argument("--no-parallel", action="store_true")

    args = parser.parse_args()

    if args.max_workers < 1:
        parser.error("--max-workers must be >= 1")
    if args.file_workers < 1:
        parser.error("--file-workers must be >= 1")
    if args.max_branches < 0:
        parser.error("--max-branches must be >= 0")

    verify = True
    if config.INSECURE:
        verify = False
        print("TLS verification: disabled (BB_INSECURE=true)")
    elif config.CA_BUNDLE:
        verify = config.CA_BUNDLE
        print(f"TLS verification: custom CA bundle ({config.CA_BUNDLE})")

    try:
        # API client: only responsible for Bitbucket HTTP communication.
        scraper = BitbucketServerScraper(
            base_url=args.server_url,
            token=args.server_token,
            verify=verify,
        )

        # Collector: project -> repo -> files (+ optional branches) -> size metadata.
        collector = RepositoryCollector(scraper)
        # Service: converts raw metadata into language distribution metrics.
        language_service = LanguageService(
            extension_classifier=ExtensionClassifier(),
            landmark_classifier=LandmarkClassifier(),
        )

        raw_repositories = collector.collect(
            parallel=not args.no_parallel,
            max_workers=args.max_workers,
            file_workers=args.file_workers,
            include_branches=args.include_branches,
            max_branches=args.max_branches,
        )
        # Final semantic report used by exporters and terminal summary.
        results = language_service.build_language_reports(raw_repositories)

    except requests.RequestException as e:
        print("Request error:", e)
        return 1

    save_csv(results, args.out_csv)
    save_json(results, args.out_json)
    print_summary(results)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
