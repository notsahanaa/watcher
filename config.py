"""
Watcher configuration.

Edit FEEDS to add your RSS feed URLs, organized by category.
Adjust LOOKBACK_HOURS for testing (default: 24 hours).
"""

# Time settings
LOOKBACK_HOURS = 360  # 15 days for testing

# RSS feeds organized by category
# Add your feeds here - the category names will appear in the digest
FEEDS = {
    "AI Tools": [
        "https://every.to/context-window/feed",
        "https://every.to/source-code/feed",
        "https://every.to/also-true-for-humans/feed",
        "https://every.to/thesis/feed"
    ],
    "Tech News": [
        # "https://techcrunch.com/feed/",
    ],
}

# Persona for Claude prompts (used in Stage 2)
PERSONA = """
You are summarizing news for a [role] who cares about [topics].
Focus on [priorities].
"""
