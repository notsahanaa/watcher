# Decisions to Revisit

Technical decisions that may need to change as Watcher evolves.

| Decision | Current | Revisit When |
|----------|---------|--------------|
| RSS metadata only | Using title/summary from feed | If Claude needs more context, add full article fetching |
| Simple sequential | Fetch feeds one by one | If feed count exceeds 50+, consider concurrent fetching |
| No retry logic | Single attempt per feed | If transient failures become frequent, add single retry |
| Content for classification | 500 words truncated | Full article + Claude summarize then synthesize/classify |
| Model choice | claude-sonnet-4-20250514 | If output quality insufficient, try opus; if cost too high, try haiku |
| Single API call | One call for all articles | If token limits hit with many articles, batch into multiple calls |
| Fixed output schema | Hardcoded JSON structure | If delivery formats need different structures, make schema configurable |
| No caching | Fresh synthesis each run | If costs become concern, cache digests and only re-synthesize on new articles |
