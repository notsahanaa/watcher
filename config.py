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
        "https://every.to/context-window/feed",
        "https://every.to/source-code/feed",
        "https://every.to/also-true-for-humans/feed",
        "https://every.to/thesis/feed"
    ],
    "Tech News": [
        # "https://techcrunch.com/feed/",
    ],
}

# Persona templates
AI_BUILDER_PERSONA = {
    "name": "AI Builder",
    "description": "Someone building AI-powered products and tools",
    "sections": ["top_highlights", "themes", "tools", "case_studies"],
    "skip": ["funding announcements", "executive hiring", "ethics debates", "policy/regulation"],
    "framing": "Focus on practical applications, implementation details, and what builders can learn or use"
}

# Active persona (set to template or custom)
ACTIVE_PERSONA = AI_BUILDER_PERSONA

# For custom personas, categories are saved here after first-run setup
CUSTOM_PERSONA_CATEGORIES = None  # Set after user confirms
