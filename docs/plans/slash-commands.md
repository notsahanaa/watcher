# Slack Slash Commands

Let users manage Watcher directly from Slack without touching code or GitHub.

## What We Built

Four slash commands that work in any Slack channel:

| Command | What It Does |
|---------|--------------|
| `/watcher-add-feed https://example.com/rss` | Adds a new RSS feed to track |
| `/watcher-add-feed https://example.com/rss "Category Name"` | Adds a feed to a specific category |
| `/watcher-remove-feed https://example.com/rss` | Stops tracking a feed |
| `/watcher-pause` | Pauses daily digests (useful for vacations) |
| `/watcher-unpause` | Resumes daily digests |

---

## Why We Built It This Way

### Decision 1: Modal for Hosting

Slack requires your server to respond within 3 seconds, but updating GitHub can take longer (especially on cold starts). We chose **Modal** because:

- It can "spawn" background tasks that keep running after responding to Slack
- Free tier is generous (90k compute-seconds/month)
- Auto-scales to zero when not in use
- Secrets are stored securely

### Decision 2: GitHub as Database

Instead of setting up a database, we store the feed list directly in `feeds.json` on GitHub:

- No database to manage or pay for
- Easy to see what feeds are tracked (just open the file)
- Version history built-in (via git commits)
- The daily digest GitHub Action already reads from there

### Decision 3: Response URL Pattern

Slack gives each command a temporary `response_url` that's valid for 30 minutes. We use this to send the success/error message back after the background work finishes. This is why you see a brief pause before the response appears.

---

## How It Works (Simple Version)

1. You type `/watcher-add-feed https://blog.example.com/rss`
2. Slack sends this to our Modal server
3. Modal immediately says "got it" (within 3 seconds, keeping Slack happy)
4. A background worker starts up and:
   - Reads current feeds from GitHub
   - Adds your new feed to the list
   - Saves the updated list back to GitHub
   - Sends a success message back to your Slack channel

---

## Setup We Did

### 1. Created the Slack App

At https://api.slack.com/apps, we:
- Created a new app called "Watcher"
- Added four slash commands pointing to Modal URLs
- Got the **Signing Secret** (proves requests really came from Slack)

### 2. Created GitHub Token

At https://github.com/settings/tokens, we:
- Created a fine-grained personal access token
- Gave it permission to read/write the `feeds.json` file
- Limited it to just the watcher repo (more secure)

### 3. Stored Secrets in Modal

We store three secrets in Modal so the code can access them:
- `GITHUB_TOKEN` - lets us update feeds.json
- `GITHUB_REPO` - which repo to update (e.g., `yourname/watcher`)
- `SLACK_SIGNING_SECRET` - verifies requests come from Slack

To update these secrets:
```bash
python3 -m modal secret create watcher-secrets --force \
  GITHUB_TOKEN="your-token-here" \
  GITHUB_REPO="yourname/watcher" \
  SLACK_SIGNING_SECRET="your-secret-here"
```

---

## Problems We Hit and Fixed

### Problem 1: "Something went wrong" on every command

**What happened:** Commands would run but always show an error.

**Why:** There's a quirk in Python's `requests` library. When sending data to the internet, it defaults to an old encoding format (latin-1) that can't handle certain characters. Slack's URLs sometimes have invisible special characters that broke this.

**Fix:** We added code to clean up text before sending it, and explicitly told Python to use modern UTF-8 encoding.

### Problem 2: "403 Forbidden" from GitHub

**What happened:** After fixing the encoding, we got permission denied errors.

**Why:** We hadn't set up a GitHub token yet - the code was trying to update GitHub anonymously.

**Fix:** Created a GitHub personal access token with permission to write files.

### Problem 3: "404 Not Found" with weird URL

**What happened:** The error showed a URL like `repos/github_pat_xxx/contents/feeds.json` - our token appeared where the repo name should be.

**Why:** When setting up Modal secrets, we accidentally put the token in the wrong field.

**Fix:** Recreated the secrets with the values in the correct fields.

---

## Deployment

Whenever you change `slack_commands.py`:

```bash
python3 -m modal deploy slack_commands.py
```

**Good news:** If you only changed secrets (not code), you don't need to redeploy. Modal picks up new secret values automatically.

---

## Testing Commands

After deploying, test in Slack:

```
/watcher-add-feed https://example.com/feed
→ Should show: "✅ Added feed to AI Tools: https://example.com/feed"

/watcher-remove-feed https://example.com/feed
→ Should show: "✅ Removed feed from AI Tools: https://example.com/feed"

/watcher-pause
→ Should show: "⏸️ Watcher paused by @yourname"

/watcher-unpause
→ Should show: "▶️ Watcher resumed by @yourname"
```

If something goes wrong, check the Modal logs:
```bash
python3 -m modal logs watcher-slack-commands
```

---

## Files Involved

| File | What It Does |
|------|--------------|
| `slack_commands.py` | All the slash command code (runs on Modal) |
| `feeds.json` | The list of RSS feeds (stored on GitHub) |
| `state.json` | Pause/unpause state (stored on GitHub) |
