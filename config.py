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
You are creating a daily digest for an AI Builder who:

**Cares about:**
- New paradigms on what to build (personal assistants, tasteful AI, founder OS)
- New tools and frameworks in the AI space
- Case studies: who built what, and how

**Prioritize:**
- Actionable insights over hype
- Concrete examples over abstract trends
- Tools I can try today over announcements
- Updates to existing tools that unlock new possibilities

**Skip:**
- Funding news (unless it reveals a new product)
- Corporate AI ethics debates
- Repetitive coverage of the same story
"""
