"""
Watcher - Personal AI News Digest

Orchestrates the three stages:
1. Ingest - Fetch content from RSS, Gmail, Substack
2. Synthesize - Process with Claude API
3. Deliver - Send via email and Slack

Usage:
    python main.py
"""

import logging
import json

from ingest import fetch_feeds

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    """Run the Watcher digest pipeline."""
    logger.info("Starting Watcher digest...")

    # Stage 1: Ingest
    logger.info("Stage 1: Fetching RSS feeds...")
    articles, summary = fetch_feeds()

    logger.info(f"Ingest complete: {summary}")

    # Print results for now (Stage 2 & 3 will process these)
    print("\n" + "=" * 60)
    print("WATCHER DIGEST - RSS ARTICLES")
    print("=" * 60)
    print(f"\nFetched {summary['articles_found']} articles from {summary['successful']}/{summary['total_feeds']} feeds")

    if summary["failed"] > 0:
        print(f"\nWarning: {summary['failed']} feeds failed:")
        for url in summary["failed_feeds"]:
            print(f"  - {url}")

    print("\n" + "-" * 60)

    # Group by category
    by_category = {}
    for article in articles:
        cat = article.get("category", "Uncategorized")
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(article)

    for category, cat_articles in by_category.items():
        print(f"\n## {category} ({len(cat_articles)} articles)\n")
        for article in cat_articles:
            print(f"- {article['title']}")
            print(f"  Source: {article['source']} | {article['published']}")
            print(f"  Link: {article['link']}")
            if article.get("content"):
                # Show content (truncated for display)
                content_preview = article["content"][:300]
                if len(article["content"]) > 300:
                    content_preview += "..."
                print(f"  {content_preview}")
            print()

    # Stage 2: Synthesize (TODO)
    logger.info("Stage 2: Synthesize - Not yet implemented")

    # Stage 3: Deliver (TODO)
    logger.info("Stage 3: Deliver - Not yet implemented")

    logger.info("Watcher digest complete.")

    return articles, summary


if __name__ == "__main__":
    main()
