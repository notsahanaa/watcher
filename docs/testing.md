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

## Testing Slack Delivery (Stage 3)

### 1. Create a Slack App

1. Go to **https://api.slack.com/apps**
2. Click **"Create New App"**
3. Choose **"From scratch"**
4. Name it (e.g., "Watcher Digest")
5. Select your workspace
6. Click **"Create App"**

### 2. Enable Incoming Webhooks

1. In the left sidebar, click **"Incoming Webhooks"**
2. Toggle **"Activate Incoming Webhooks"** to **ON**
3. Scroll down and click **"Add New Webhook to Workspace"**
4. Select the channel where you want digests posted (e.g., #watcher-test)
5. Click **"Allow"**

### 3. Copy the Webhook URL

After allowing, you'll see a new webhook URL like:
```
https://hooks.slack.com/services/<workspace-id>/<channel-id>/<token>
```

Copy this URL.

### 4. Configure Environment

Add the webhook URL to your `.env` file:

```bash
# .env
ANTHROPIC_API_KEY=your-api-key-here
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

### 5. Run and Verify

```bash
python3 main.py
```

**Expected terminal output:**
```
2026-03-30 ... - Stage 1: Fetching RSS feeds...
2026-03-30 ... - Stage 2: Synthesizing with Claude...
2026-03-30 ... - Stage 3: Delivering to Slack...
2026-03-30 ... - Delivered to Slack
2026-03-30 ... - Watcher digest complete.
```

**Expected in Slack:**
A formatted message with:
- Header with date
- Top Highlights with source links
- Themes with article summaries
- New Tools / Tool Updates
- Footer with feed statistics

### Slack Delivery Scenarios

| Scenario | Expected Behavior |
|----------|-------------------|
| No `SLACK_WEBHOOK_URL` set | Skips delivery, logs "Slack delivery skipped" |
| Invalid webhook URL | Logs warning with error, continues without crashing |
| Empty digest (no articles) | Skips delivery, logs "No digest to deliver" |
| Slack API down | Logs warning with error, continues without crashing |

### Unit Tests

```bash
# Run Slack-specific tests
python3 -m pytest tests/test_slack.py -v
```

Tests verify:
- Correct Block Kit payload format
- Handles missing webhook URL
- Handles API errors gracefully
- Handles network errors gracefully

---

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

### Slack delivery skipped
- Check that `SLACK_WEBHOOK_URL` is set in `.env`
- Verify the URL starts with `https://hooks.slack.com/services/`

### Slack delivery failed
- Verify your webhook URL is correct and active
- Check if the Slack app is still installed in your workspace
- Test the webhook manually:
  ```bash
  curl -X POST -H 'Content-type: application/json' \
    --data '{"text":"Test message"}' \
    $SLACK_WEBHOOK_URL
  ```

### Message not appearing in Slack
- Check you're looking at the correct channel (the one you selected when creating the webhook)
- Verify the webhook wasn't revoked in Slack app settings
