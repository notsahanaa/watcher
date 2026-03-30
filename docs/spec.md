# Watcher — Design Spec

**Date:** 2026-03-30
**Status:** Stage 3 Complete
**Stages:** 1 (Ingest) ✓, 2 (Synthesize) ✓, 3 (Deliver) ✓

## Overview

Watcher is a personal AI news digest agent. Every day it ingests content from RSS feeds, Gmail newsletters, and Substack subscriptions, synthesizes them using the Claude API, and delivers a structured digest to email and Slack.

This spec covers **Stage 1 (Ingest)**, **Stage 2 (Synthesize)**, and **Stage 3 (Deliver)**.

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
│   ├── __init__.py
│   └── synthesizer.py         # Claude API synthesis
├── deliver/
│   ├── __init__.py            # Package exports
│   └── slack.py               # Slack webhook delivery
├── docs/
│   └── testing.md             # Testing guide and decisions
├── requirements.txt
└── .gitignore
```

Note: Set `ANTHROPIC_API_KEY` environment variable for Stage 2. `.env.example` to be added in Stage 3.

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

See [decisions-to-revisit.md](decisions-to-revisit.md)

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

## Stage 2: Synthesize

### Overview

Takes articles from Stage 1 and sends them to Claude API for synthesis into a structured digest with highlights, themes, and tools.

### Output Format

```python
{
    "top_highlights": [
        {
            "insight": "3-4 line summary of a key insight",
            "source": "example.com",
            "link": "https://example.com/article"
        }
    ],
    "themes": [
        {
            "name": "Theme Name",
            "subthemes": ["subtheme1", "subtheme2"],
            "articles": [
                {
                    "title": "Article title",
                    "summary": "1-2 sentence summary",
                    "use_case": "How this applies to the persona",
                    "link": "https://example.com/article"
                }
            ]
        }
    ],
    "tools": {
        "new": [
            {
                "name": "Tool Name",
                "description": "What it does",
                "why_notable": "Why the persona should care",
                "link": "https://example.com/article"
            }
        ],
        "updates": [
            {
                "name": "Tool Name",
                "update": "What changed",
                "why_notable": "Why this update matters",
                "link": "https://example.com/article"
            }
        ]
    },
    "skipped_count": 0,
    "skipped_reasons": ["List of reasons articles were skipped"]
}
```

### Functions

| Function | Purpose |
|----------|---------|
| `synthesize(articles)` | Main entry point. Returns `(digest, error)` |
| `_build_prompt(articles)` | Constructs prompt with persona and articles |
| `_parse_response(content)` | Parses JSON from Claude response |

### Decisions Made

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Model | `claude-sonnet-4-20250514` | Balance of quality, speed, and cost |
| Max tokens | 4096 | Sufficient for digest response |
| Output format | Structured JSON | Enables programmatic display and future delivery formats |
| JSON parsing | Direct parse + markdown code block fallback | Claude sometimes wraps response in ```json blocks |
| Content source | Full article content (500 words truncated) | More context than RSS summary alone |
| Persona location | `config.py` PERSONA variable | User-editable without touching code |
| Error handling | Return `(None, error_message)` tuple | Caller decides how to handle failures |
| Empty articles | Return early with error | No point calling API with nothing |

### Dependencies

```
anthropic>=0.18.0
python-dotenv>=1.0.0
```

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | Claude API key |

### Stage 2 Deliverables

- [x] `synthesize/__init__.py` — Package exports
- [x] `synthesize/synthesizer.py` — Synthesis logic
- [x] `tests/test_synthesizer.py` — Unit tests
- [x] `config.py` PERSONA — Customizable persona

---

## Stage 3: Deliver (Slack)

### Overview

Posts the synthesized digest to Slack via incoming webhook. Delivery happens automatically if `SLACK_WEBHOOK_URL` environment variable is set.

### Functions

| Function | Purpose |
|----------|---------|
| `deliver_to_slack(digest, summary)` | Main entry point. Returns `(success, error)` |
| `format_digest_for_slack(digest, summary)` | Converts digest to Slack Block Kit format |

### Slack Message Format

The digest is formatted using Slack Block Kit with:
- Header with date
- Top Highlights section with source links
- Themes section with subthemes and article summaries
- New Tools and Tool Updates sections
- Footer with feed statistics

### Decisions Made

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Delivery channel | Slack webhook | Simple, no OAuth, just POST |
| Trigger | Always deliver if env var set | Hands-off for daily cron |
| Formatting | Slack Block Kit | Rich formatting, supports links |
| Error handling | Log and continue | Don't fail the pipeline if Slack is down |
| No digest case | Skip delivery, log info | Nothing to send |

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SLACK_WEBHOOK_URL` | No | If set, posts digest to this webhook |

### Error Handling

- **Missing webhook URL:** Skip delivery silently (info log)
- **Webhook error:** Log warning, return error message, don't crash
- **Empty digest:** Skip delivery (nothing to send)

### Stage 3 Deliverables

- [x] `deliver/slack.py` — Slack posting logic
- [x] `deliver/__init__.py` — Package exports
- [x] `tests/test_slack.py` — Unit tests
- [x] `main.py` — Stage 3 integration
- [x] `requirements.txt` — Added requests
- [x] `.env.example` — Documented env vars

---

## Future Stages

- **Stage 4 (Email):** Send digest via Resend email API
