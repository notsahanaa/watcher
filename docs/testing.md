# Watcher Testing Guide

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run unit tests
python -m pytest tests/ -v

# Run the fetcher manually
python main.py
```

## Testing RSS Fetcher

### 1. Add Test Feeds

Edit `config.py` and add some real RSS feeds:

```python
FEEDS = {
    "AI Tools": [
        "https://openai.com/blog/rss.xml",
        "https://blog.anthropic.com/rss.xml",
    ],
    "Tech News": [
        "https://techcrunch.com/feed/",
        "https://www.theverge.com/rss/index.xml",
    ],
}
```

### 2. Adjust Time Window (Optional)

If feeds haven't published recently, increase the lookback:

```python
LOOKBACK_HOURS = 72  # 3 days instead of 24 hours
```

### 3. Run and Verify

```bash
python main.py
```

Check that:
- Articles are grouped by category
- Each article has title, source, link, published date
- No duplicate URLs appear
- Failed feeds are logged (if any)

## Unit Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test class
python -m pytest tests/test_rss_fetcher.py::TestFetchFeeds -v

# Run with coverage
python -m pytest tests/ --cov=ingest --cov-report=term-missing
```

## Decisions to Revisit

| Decision | Current | Revisit When |
|----------|---------|--------------|
| RSS metadata only | Using title/summary from feed | If Claude needs more context, add full article fetching |
| Simple sequential | Fetch feeds one by one | If feed count exceeds 50+, consider concurrent fetching |
| No retry logic | Single attempt per feed | If transient failures become frequent, add single retry |

## Troubleshooting

### "No feeds configured"
Add feeds to `config.py` in the `FEEDS` dict.

### "0 articles found" with feeds configured
- Check if feeds have published in the last 24 hours
- Increase `LOOKBACK_HOURS` to 48 or 72
- Verify feed URLs are correct (test in browser)

### Feed errors
Check the logs for specific error messages. Common issues:
- Network timeouts
- Invalid RSS/XML format
- Feed URL changed or deprecated
