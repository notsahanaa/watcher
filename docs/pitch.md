# Watcher

## The Problem

Staying on top of your industry is chaos.

We live in a time where tech, the potential it brings, and the systems that enable it are rapidly growing. For anyone hoping to build something successful in this era, keeping on top of "what is possible and who is enabling it" as well as knowing what is becoming less important is table stakes. Yet with tons of newsletters, podcasts, company announcements, and other sources constantly pushing out information, it is easy to miss what is important if you're not spending tons of time scrolling through your news feeds.

To get a sense for how existing founders and investors were solving this problem, we talked to founders from PSL and UW Comotion. They did not have a charming answer. It was either "I read everything I can get my hands on, but there's no system; if you can find one, please let me know" or "I don't really know where to get started sometimes and I constantly feel like I'm missing important information."


## The Solution

**Watcher**: Your AI agent for industry intelligence.

AI agents exist to do everything—but none exist to watch the industry for you.

Watcher learns your angles and interests. It constantly monitors all your newsletters, podcasts, subscriptions, and company/tool updates. Then it surfaces what matters on a daily basis: actionable, high-priority themes with source links. Think of it as a prioritized, customized feed built from all your trusted knowledge sources—so you learn what you need at a glance. Extract signal from noise.

## How It Works

1. **Give your Watcher a persona** — Are you an AI builder? A tech investor? A product leader? Watcher tailors its lens to your role.

2. **Connect your knowledge sources** — RSS feeds, newsletters, podcasts, and company blogs with our one-click integrations. Watcher ingests what you already trust.

3. **Check back daily** — See what Watcher has surfaced for you. High-priority insights, emerging themes, and actionable intelligence—all in one place.

4. **View trends over time** — Track industry patterns and cross-connections across your knowledge base. Spot what's emerging and diminishing.

5. **Ask Watcher to dig deeper** — Have a question? Watcher can explore further, pulling from your accumulated knowledge to give you context-rich answers.

## Bring Watcher Into Your Life

**Option 1: Free Self-Hosted (during testing phase only)**
Clone the repo and add your own Claude API key. Full control, no dependencies.

**Option 2: MCP Integration**
Use the Watcher MCP to connect it directly to your personal agent ecosystem. Watcher becomes part of your AI workflow.

**Option 3: Watcher Web**
Create an account to access your feeds and trends from a visual web and mobile interface.

---

## Why Not Build It Yourself?

Watcher is an AI agent. Tech-savvy users could theoretically build something similar. Here's why they won't—and why Watcher's moat deepens with scale:

### Shared Understanding, Shared Costs

Every article in Watcher's database is analyzed once and understood for everyone. When a new post drops from a16z or a key AI research paper hits arXiv, Watcher processes it once—then serves insights to thousands of users. DIY means paying full inference costs for every article, every time. At scale, this becomes untenable. Watcher amortizes the cost of intelligence across its entire user base, making high-quality synthesis economically viable at prices individuals can afford.

### Curated Sources, Zero Research

Finding high-signal feeds is its own research project. Which newsletters actually matter? Which company blogs are worth tracking? Which podcasts have signal vs. noise? Watcher ships with pre-built, one-click connections to reputed sources—actively managed for quality.

### Quality Through Iteration

Building a system that surfaces *good* insights—not just *any* insights—is hard. It requires tuning search mechanisms, refining synthesis prompts, and iterating based on real-world feedback across diverse use cases. Watcher's retrieval and synthesis pipelines are the result of extensive experimentation which would be hard to achieve individually without significant time investments 

---

## Competitive Landscape

The current market is fragmented between basic RSS readers and expensive enterprise tools—with nothing built for founders and builders in between.

### RSS Readers (Feedly, Inoreader, Feeder)

**What they do:** Aggregate RSS feeds into a single interface.

**Where they fall short:**
- **No true intelligence layer** — They organize content but don't synthesize it. You still read everything manually.
- **AI features are surface-level** — Feedly's "Leo" AI can filter and tag, but it's keyword matching, not understanding. No trend detection, no cross-source synthesis.
- **Persona-blind** — They don't adapt to *who you are*. An AI builder and a marketing lead see the same feed.
- **Pricing friction** — Feedly locks AI features behind $99+/year Pro+ plans (annual-only billing). 
- **Overwhelming at scale** — Users report feeds become unmanageable without constant manual triage. Too many sources = chaos.
- **No actionable output** — You get a river of articles, not prioritized insights you can act on.

### Enterprise Intelligence (AlphaSense)

**What they do:** AI-powered market intelligence for financial institutions and large enterprises.

**Where they fall short:**
- **Prohibitively expensive** — $10,000–$100,000+/year. Built for hedge funds, not indie hackers.
- **Overkill for builders** — Optimized for SEC filings and broker research, not tech blogs and AI newsletters.
- **Not for light use** — "Quick & dirty checks" aren't the use case. Requires commitment.

### Defunct Attempts (Artifact)

Instagram's co-founders launched Artifact—an AI-powered personalized news app. It shut down in January 2024. Their conclusion: *"The market opportunity isn't big enough."*

But they were solving the wrong problem. Artifact tried to replace your news diet. Watcher amplifies the sources you already trust.

### The Gap Watcher Fills

| Feature | RSS Readers | AlphaSense | Watcher |
|---------|-------------|------------|---------|
| Persona-aware filtering | No | Partial | Yes |
| Cross-source trend synthesis | No | Yes | Yes |
| Your trusted sources only | Yes | No | Yes |
| Affordable for individuals | Partial | No | Yes |
| Conversational follow-up | No | Limited | Yes |
| Actionable daily brief | No | Yes | Yes |

**Watcher sits in the white space**: intelligence-grade synthesis at indie-hacker prices, built on *your* sources, tailored to *your* role.

---

## Market Size

### The Opportunity

Watcher operates at the intersection of three growing markets:

| Market | 2025 Size | Projected | CAGR |
|--------|-----------|-----------|------|
| News Aggregator | $2.5B | $5.1B (2032) | 9.3% |
| Competitive Intelligence Tools | $500M–$7B | $1.5B–$15B (2030–34) | 12–14% |
| Business Intelligence (broader) | $35B | $56B (2030) | 8.2% |

### Competitor Benchmarks

| Company | Revenue | Valuation | Employees | Users/Customers |
|---------|---------|-----------|-----------|-----------------|
| **Feedly** | $7.3M ARR | — | 66 | 14M+ registered |
| **Inoreader** | $5.9M | Bootstrapped | 14 | Millions (est.) |
| **AlphaSense** | $500M ARR | $4B | 1,500+ | 6,500 enterprises |

### Key Insights

**RSS readers are a $7–13M/year business** at the top end (Feedly + Inoreader combined ~$13M). These are profitable, bootstrapped-scale businesses—but they've plateaued. Feedly holds 99% of the RSS reader market share, yet AI features remain surface-level. The ceiling is low because the product is low-value: aggregation without intelligence.

**Enterprise intelligence is a $500M+ ARR market**—but it's inaccessible. AlphaSense raised $1.6B and serves hedge funds at $10K–$100K/year. 85% of S&P 100 companies use it. But founders, indie hackers, and small teams are priced out entirely.

**The white space is massive.** There's no product delivering AlphaSense-quality intelligence at Feedly-level pricing. The news aggregator market alone is $2.5B and growing 9% annually—driven by demand for AI-powered personalization and filtering.

### Watcher's Addressable Market

- **Primary TAM**: Tech founders, AI builders, product leaders, and investors who need industry intelligence but can't afford enterprise tools. Estimated 5–10M professionals globally.
- **Wedge**: Self-hosted + MCP-native appeals to the AI-native builder crowd—early adopters who influence purchasing decisions at scale.
- **Expansion**: Watcher Web brings the same intelligence to teams and orgs, opening B2B revenue.

**Bottom line**: The market validated that people pay for feed aggregation ($13M in RSS revenue) and that enterprises pay for intelligence ($500M at AlphaSense). Watcher bridges the gap—intelligence-grade insights for the other 99%.

**Market Size & Revenue Data**
- [Feedly Revenue & Stats - Latka](https://getlatka.com/companies/feedly.com)
- [Feedly Market Share - 6sense](https://6sense.com/tech/rss-readers/feedly-market-share)
- [Inoreader Company Profile - Owler](https://www.owler.com/company/inoreader)
- [AlphaSense Revenue - Latka](https://getlatka.com/companies/alphasense)
- [AlphaSense Funding - Sacra](https://sacra.com/c/alphasense/)
- [News Aggregator Market Size - Market Research Intellect](https://www.marketresearchintellect.com/product/news-aggregator-market/)
- [RSS Reader Market Forecast - OpenPR](https://www.openpr.com/news/4219419/global-really-simple-syndication-rss-reader-market-set-to-reach)
- [Competitive Intelligence Tools Market - Mordor Intelligence](https://www.mordorintelligence.com/industry-reports/competitive-intelligence-tools-market)
- [Business Intelligence Market - Mordor Intelligence](https://www.mordorintelligence.com/industry-reports/global-business-intelligence-bi-vendors-market-industry)


---

## Sources

- [Feedly Reviews 2026 - Capterra](https://www.capterra.com/p/202497/Feedly/reviews/)
- [Feedly vs Inoreader Free Plan Limits - Readless](https://www.readless.app/blog/feedly-vs-inoreader-free-plan-limits-2026)
- [Inoreader vs Feedly Comparison - Slant](https://www.slant.co/versus/1455/1461/~feedly_vs_inoreader)
- [AlphaSense Pricing - Vendr](https://www.vendr.com/marketplace/alphasense)
- [AlphaSense Review - Research.com](https://research.com/software/reviews/alphasense)
- [Best AI News Aggregators 2026 - Readless](https://www.readless.app/blog/best-ai-news-aggregators-2026)
- [Artifact App - Wikipedia](https://en.wikipedia.org/wiki/Artifact_(app))
- [Navigating AI News Overload - Agentic Foundry](https://www.agenticfoundry.ai/post/navigating-ai-news-overload-start-with-a-problem-first-mindset)


---

*Stop drowning in information. Start knowing what matters.*
