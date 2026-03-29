"""
Watcher configuration.

Edit FEEDS to add your RSS feed URLs, organized by category.
Adjust LOOKBACK_HOURS for testing (default: 24 hours).
"""

# Time settings
LOOKBACK_HOURS = 24  # How far back to fetch articles

# RSS feeds organized by category
# Add your feeds here - the category names will appear in the digest
FEEDS = {
    "AI Tools": [
        # Example: "https://openai.com/blog/rss.xml",
    ],
    "Tech News": [
        # Example: "https://techcrunch.com/feed/",
    ],
}

# Persona for Claude prompts (used in Stage 2)
PERSONA = """
You are summarizing news for a [role] who cares about [topics].
Focus on [priorities].
"""
