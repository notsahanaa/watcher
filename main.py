"""
Watcher - Personal AI News Digest

Orchestrates the three stages:
1. Ingest - Fetch content from RSS, Gmail, Substack
2. Synthesize - Process with Claude API
3. Deliver - Send via email and Slack

Usage:
    python main.py
"""

import json
import logging

from ingest import fetch_feeds
from synthesize import synthesize
from deliver import deliver_to_slack

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
                # Show full content for testing
                word_count = len(article["content"].split())
                print(f"  [Content: {word_count} words]")
                print(f"  {article['content']}")
                print()
            print()

    # Stage 2: Synthesize
    logger.info("Stage 2: Synthesizing with Claude...")
    digest, synth_error = synthesize(articles)

    if synth_error:
        logger.error(f"Synthesis failed: {synth_error}")
        print(f"\nSynthesis Error: {synth_error}")
    elif digest:
        print("\n" + "=" * 60)
        print("WATCHER DIGEST - SYNTHESIZED")
        print("=" * 60)

        # Top Highlights
        if digest.get("top_highlights"):
            print("\n## TOP HIGHLIGHTS\n")
            for i, highlight in enumerate(digest["top_highlights"], 1):
                print(f"{i}. {highlight['insight']}")
                print(f"   Source: {highlight.get('source', 'N/A')} | {highlight.get('link', '')}")
                print()

        # Themes
        if digest.get("themes"):
            print("\n## THEMES\n")
            for theme in digest["themes"]:
                subthemes = ", ".join(theme.get("subthemes", []))
                print(f"### {theme['name']}")
                if subthemes:
                    print(f"    Subthemes: {subthemes}")
                for article in theme.get("articles", []):
                    print(f"    - {article['title']}")
                    print(f"      {article.get('summary', '')}")
                    if article.get("use_case"):
                        print(f"      Use case: {article['use_case']}")
                    print()

        # Tools
        tools = digest.get("tools", {})
        if tools.get("new"):
            print("\n## NEW TOOLS\n")
            for tool in tools["new"]:
                print(f"- **{tool['name']}**: {tool['description']}")
                print(f"  Why notable: {tool.get('why_notable', 'N/A')}")
                print(f"  Link: {tool.get('link', 'N/A')}")
                print()

        if tools.get("updates"):
            print("\n## TOOL UPDATES\n")
            for tool in tools["updates"]:
                print(f"- **{tool['name']}**: {tool['update']}")
                print(f"  Why notable: {tool.get('why_notable', 'N/A')}")
                print(f"  Link: {tool.get('link', 'N/A')}")
                print()

        # Skipped
        if digest.get("skipped_count", 0) > 0:
            print(f"\n[Skipped {digest['skipped_count']} articles: {', '.join(digest.get('skipped_reasons', []))}]")

    # Stage 3: Deliver
    if digest:
        logger.info("Stage 3: Delivering to Slack...")
        success, error = deliver_to_slack(digest, summary)
        if success:
            logger.info("Delivered to Slack")
        elif error:
            logger.warning(f"Slack delivery failed: {error}")
        else:
            logger.info("Slack delivery skipped (no webhook configured)")
    else:
        logger.info("Stage 3: No digest to deliver")

    logger.info("Watcher digest complete.")

    return articles, summary, digest if digest else None


if __name__ == "__main__":
    main()
