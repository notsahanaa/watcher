# Watcher RSS Fetcher — Design Spec

**Date:** 2026-03-29
**Status:** Approved
**Stage:** 1 of 3 (Ingest)

## Overview

Watcher is a personal AI news digest agent. Every day it ingests content from RSS feeds, Gmail newsletters, and Substack subscriptions, synthesizes them using the Claude API, and delivers a structured digest to email and Slack.

This spec covers **Stage 1: RSS Fetcher** — the first ingest source.

## Project Structure

```
watcher/
├── .github/
│   └── workflows/
│       └── daily_digest.yml   # Cron job: runs main.py at 5am
├── config.py                  # Persona, feed URLs, settings
├── main.py                    # Orchestrates all 3 stages
├── ingest/
│   ├── __init__.py
│   └── rss_fetcher.py         # RSS fetching logic
├── synthesize/
│   └── __init__.py            # (Stage 2 - future)
├── deliver/
│   └── __init__.py            # (Stage 3 - future)
├── docs/
│   └── testing.md             # Testing guide and decisions
├── requirements.txt
└── .gitignore
```

Note: `.env.example` will be added in Stage 2/3 when API keys are needed.

## config.py

```python
# Time settings
LOOKBACK_HOURS = 24  # Configurable for testing

# RSS feeds organized by category
FEEDS = {
    "AI Tools": [
        # Add feed URLs here
    ],
    "Tech News": [
        # Add feed URLs here
    ],
}

# Persona for Claude prompts (Stage 2)
PERSONA = """
You are summarizing news for a [role] who cares about [topics].
Focus on [priorities].
"""
```

## rss_fetcher.py

### Responsibilities

1. Read feed URLs from config (by category)
2. Fetch each feed sequentially using `feedparser`
3. Filter to articles within the time window (default: 24 hours)
4. Dedupe by URL (same URL in multiple feeds = keep one)
5. Return clean list of articles + fetch summary

### Output Format

```python
# Articles list
[
    {
        "title": "Article Title",
        "summary": "The article description/summary from RSS",
        "link": "https://example.com/article",
        "source": "example.com",       # Extracted from feed URL domain
        "category": "AI Tools",
        "published": "2026-03-28T14:30:00Z"  # ISO format, UTC
    },
    # ... more articles
]

# Fetch summary (for error reporting)
{
    "total_feeds": 10,
    "successful": 8,
    "failed": 2,
    "failed_feeds": ["https://broken.com/feed", "https://down.com/rss"],
    "articles_found": 45
}
```

### Functions

| Function | Purpose |
|----------|---------|
| `fetch_feeds()` | Main entry point. Returns `(articles, summary)` |
| `_fetch_single_feed(url, category)` | Fetches one feed, handles errors |
| `_is_within_window(entry, cutoff_time)` | Checks if article is recent enough |
| `_get_cutoff_time()` | Returns datetime for LOOKBACK_HOURS ago (UTC) |
| `_dedupe_by_url(articles)` | Removes duplicate URLs |
| `_extract_source(feed_url)` | Extracts domain from feed URL for source field |
| `_parse_entry_date(entry)` | Extracts publication date from RSS entry |

### Timezone Handling

- **All internal comparisons use UTC** to avoid timezone ambiguity
- `_get_cutoff_time()` returns a UTC datetime (current time minus LOOKBACK_HOURS)
- RSS entry dates are normalized to UTC using `python-dateutil`
- If an RSS entry has a timezone-aware date, convert to UTC
- If an RSS entry has a naive date, assume UTC

### Date Field Extraction

RSS entries may use different fields for publication date. Check in this order:

1. `published_parsed` (feedparser's parsed struct_time)
2. `updated_parsed` (fallback if no published date)
3. If neither exists: **skip the article** and log a debug message

### Source Field Extraction

The `source` field is extracted from the **feed URL** (not the article URL):

```python
# Feed URL: https://techcrunch.com/feed/
# Extracted source: "techcrunch.com"
```

Use `urllib.parse.urlparse(feed_url).netloc` to extract the domain.

### Error Handling

- **Per-feed errors:** Log warning with feed URL and error message, skip feed, continue with others
- **Malformed entries:** Skip individual entries that lack required fields (title, link, date)
- **Logging:** Use Python's `logging` module (captured by GitHub Actions)
- **Summary:** Return failed feed count and URLs for Slack notification (Stage 3)
- **No retry logic:** Keep it simple; transient failures will be caught in the next daily run

### Empty Feeds Handling

- A feed that returns successfully but has no entries within the time window counts as **successful** in the summary
- This is expected behavior (some feeds may not publish daily)
- The `articles_found` count in the summary shows total articles across all feeds

### Input Validation

On startup, `fetch_feeds()` validates config:

- If `FEEDS` is empty or missing: log warning, return empty list with summary indicating 0 feeds
- If a category has an empty URL list: skip that category, log debug message
- If a URL is malformed: treat as a failed fetch (feedparser will error), continue with others

## Decisions Made

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Time window | 24-hour rolling | Simple, predictable, configurable |
| Cron schedule | 5 AM system timezone | Early morning digest |
| Feed organization | Categorized dict | Helps Claude organize digest by theme |
| Content extraction | RSS metadata only | Fast, simple, sufficient for summaries |
| Deduplication | Basic URL dedup | Same URL = same article; different URLs covering same topic = keep both for source attribution |
| Fetching approach | Simple sequential | Daily job, speed not critical |
| Error handling | Skip and log | One broken feed shouldn't stop the digest |
| Timezone handling | Normalize to UTC | Consistent comparisons regardless of feed timezone |
| Missing dates | Skip article | Better to miss one article than show stale content |

## Decisions to Revisit

| Decision | Current | Revisit When |
|----------|---------|--------------|
| RSS metadata only | Using title/summary from feed | If Claude needs more context, add full article fetching |
| Simple sequential | Fetch feeds one by one | If feed count exceeds 50+, consider concurrent fetching |
| No retry logic | Single attempt per feed | If transient failures become frequent, add single retry |

## Data Flow

```
config.py (FEEDS)
      │
      ▼
rss_fetcher.fetch_feeds()
      │
      ├── Validate config
      │
      ├─► Fetch feed 1 ─► Parse entries ─► Filter by time ─► Add to list
      ├─► Fetch feed 2 ─► Parse entries ─► Filter by time ─► Add to list
      ├─► Fetch feed 3 ─► (fails) ─► Log warning, continue
      └─► ...
      │
      ▼
Dedupe by URL
      │
      ▼
Return (articles, summary)
      │
      ▼
main.py passes to Stage 2 (Synthesize)
```

## Dependencies

```
feedparser>=6.0.0
python-dateutil>=2.8.0
```

## Stage 1 Deliverables

- [x] `config.py` — Settings and feed URLs
- [x] `ingest/__init__.py` — Package marker
- [x] `ingest/rss_fetcher.py` — Fetching logic
- [x] `main.py` — Skeleton orchestrator
- [x] `requirements.txt` — Dependencies
- [x] `docs/testing.md` — Testing guide
- [x] `.gitignore` — Standard Python ignores

## Future Stages

- **Stage 2 (Synthesize):** Send articles to Claude API, extract themes, dedupe semantically
- **Stage 3 (Deliver):** Send digest via Resend (email) and Slack webhook, including error summary
