# Revised Morning Briefing Plan

## From your perspective: what should this be?

When you wake up and open this, it should feel like a smart colleague who knows your stack left you a note. Not a news feed.

**You should be able to:**
1. Glance at the top story in 3 seconds and know if it matters
2. See a clear action for each item (adopt / try / track / note)
3. Tap any source link to read the full article
4. Get a specific "one move today" — an actual thing to do, not a platitude
5. Finish reading in under 2 minutes

**What the briefing communicates:**
- **Top story** — one thing that matters right now for *your* build, with a personal take
- **Actions** — not just news, but what to do about it: "install this plugin", "read this post", "try this workflow"
- **Signals** — 3-4 other items, each tagged with action level
- **Sources** — every item has a clickable link with publication name
- **Radar** — 1-2 things to watch over time (not daily news, but trends)
- **One move today** — a concrete next action, informed by the content

---

## What's wrong with the current approach

| Current | Problem |
|---|---|
| Python scores articles by keyword matching | No real editorial judgment. Generic content |
| Template fills ~10 sections with static/generated text | Scattered, hard to scan, placeholder filler |
| 12+ articles gathered, all shoved into template | No curation — everything gets equal treatment |
| Links exist in HTML but layout buries them | User can't find sources |
| No personal take | "Here's what happened" not "here's why you should care" |
| Content is generic AI news | Doesn't reference Hermes, Nanobot, or user's actual projects |

---

## Proposed new architecture

### Cast a wide net, curate tightly

```
Step 1: Wide sweep
  Agent runs 8-10 targeted searches across different sources
  → gathers 20-40 raw results (title + description)
  
Step 2: Smart filtering
  Agent skims titles + descriptions, picks 8-12 promising candidates
  → extracts full content from those (cost-efficient: extract only what's worth reading)

Step 3: Editorial curation
  Agent reads the 8-12 articles
  → selects the 5-7 that genuinely matter for Alex's build
  → writes personal takes, assigns action tags, ensures links

Step 4: Render
  Python pipeline takes the editorial JSON → renders HTML shell
  (Zero content generation. Zero static text. Pure rendering.)
```

This way you get broad coverage (many sources checked) without paying to extract 40 articles. The agent skims cheap search result metadata, then only extracts the promising ones.

---

## Relationship to the official Hermes Agent tutorial

The official [Tutorial: Daily Briefing Bot](https://hermes-agent.nousresearch.com/docs/guides/daily-briefing-bot) covers a simpler version of this same idea — a self-contained cron prompt that searches, summarizes, and delivers plain text to Telegram/Discord. Zero code. Just a prompt.

Our plan is a **premium variant** on top of that same pattern:

| Dimension | Official Tutorial | Our Plan |
|-----------|-----------------|----------|
| Curation | Agent summarizes top N stories | Agent writes personal takes + action tags |
| Output | Plain text message ("☀️ Your AI Briefing") | Custom dark/amber HTML artifact |
| Structure | Flat list of headlines + links | Top story → signals → radar → one move |
| Action guidance | None | Adopt / Try / Track / Note tags |
| Delivery | Direct message (text) | HTML attachment + direct message |
| Build cost | Zero | ~$0.11-0.16/day |

Both routes use the same core architecture: agent does the work, cron drives it, web search feeds it, Telegram delivers it. Our version adds editorial depth and a polished reading surface on top.

**Key insight from the official tutorial — the golden rule:** Cron jobs run in a completely fresh session with no memory of previous conversations. Every prompt must be fully self-contained. This replaces our earlier "user context file" idea — it's simpler and more reliable to bake Alex's profile directly into the cron prompt.

---

## Best practices from real newsletters

### Signal density
Every item should answer: what happened + why it matters for you + what to do about it. If an item can't answer all three, it's either radar (watch) or not worth including.

### Hierarchy
- **One big thing** — the most important story gets a few sentences and the most prominent position
- **Supporting signals** — shorter, grouped by theme or action tag
- **Radar** — brief, no action needed, just awareness

### Content mix
Not everything should be **Adopt** or **Try**. A healthy briefing has variety:
- 1 **Adopt** (something to integrate)
- 2-3 **Try** (experiments, new tools, workflows)
- 1-2 **Track** (trends, upcoming releases)
- 1 **Note** (context, industry moves, pricing changes)

### Source diversity
Mix of sources: official announcements (OpenAI, Google, GitHub), community (Reddit, Discord, blogs), tools (GitHub repos, product launches), analysis (papers, benchmarks).

### Personal voice
The "why this matters" take should reference the user's actual stack. For example:
> "Google's new MCP plugin — This directly affects how your Hermes agents discover and use tools. Worth reading the spec this week."

### Brevity
- Top story: 3-4 sentences max
- Signals: 1-2 sentences each
- Radar: 1 sentence each
- One move: 1 sentence + optional link

### Every item has a visible source
Format: `Headline → Source Name · [Link]`

No buried links. No `href="#"`. Every article reference is one tap away from the full read.

---

## Updated content model

### Editorial JSON (what the cron agent writes)

```json
{
  "issue": {
    "number": 1,
    "date": "June 5, 2026",
    "time": "6:30 AM PT",
    "sources_scanned": 28,
    "articles_read": 9
  },
  "top_story": {
    "headline": "MCP protocol v2 adds dynamic tool discovery",
    "source": "Anthropic Blog",
    "url": "https://...",
    "take": "This changes how your Hermes agents discover and bind tools at runtime. The old static tool registry approach will need updating, but the flexibility gain is significant.",
    "tag": "adopt",
    "why_now": "Your Hermes agent build is at the right stage to adopt this — early enough to avoid migration pain, late enough that the spec is stable."
  },
  "signals": [
    {
      "headline": "llama.cpp 2x speculative decoding speedup",
      "source": "GitHub · ggerganov",
      "url": "https://...",
      "take": "If you're running local inference for Hermes test loops, this is worth trying this week.",
      "tag": "try"
    },
    {
      "headline": "Gemini 3.5 Flash drops to $0.10/M tokens",
      "source": "Google AI",
      "url": "https://...",
      "take": "Good eval budget option for Hermes CI runs. At this price you can run eval suites 5x larger for the same cost.",
      "tag": "track"
    },
    {
      "headline": "Cursor adds native MCP server support",
      "source": "Cursor Blog",
      "url": "https://...",
      "take": "If you use Cursor for Hermes development, this lets your editor directly interact with your agent tools.",
      "tag": "try"
    },
    {
      "headline": "OpenAI changes reasoning model pricing",
      "source": "OpenAI",
      "url": "https://...",
      "take": "Worth noting for cost planning but doesn't change your current Hermes workflow.",
      "tag": "note"
    }
  ],
  "radar": [
    "Agent memory benchmark standardization — could affect Hermes memory module design in Q3",
    "WebGPU inference reaching production quality — potential for browser-based Hermes workers"
  ],
  "one_move": "Read the MCP v2 dynamic discovery spec and map it against your current Hermes tool registry. Key question: does dynamic discovery replace or complement your static tool contracts?"
}
```

### Source scanning notice
The top rail shows: `sources scanned: 28 · articles read: 9` — so Alex knows the briefing is curated, not just the top 5 search results. This builds trust.

---

## Action tags refined

| Tag | Color | Meaning | When to use |
|---|---|---|---|
| **Adopt** | Green | Integrate into your stack now | Directly relevant to current build, stable, well-documented |
| **Try** | Amber | Worth experimenting with | Interesting approach, but needs evaluation first |
| **Track** | Blue | Watch for maturity | Too early to commit, but significant trend |
| **Note** | Muted | Context worth having | Industry news, pricing changes, announcements |

---

## Cost analysis (updated)

| Component | Cost per run |
|---|---|
| 8-10 web searches (titles + descriptions only) | ~$0.02 |
| Extract 8-12 articles (from ~30 candidates) | ~$0.04 |
| LLM reading + writing editorial JSON | ~$0.05-0.10 |
| Python rendering | $0 |
| Telegram delivery | $0 |
| **Total per day** | **~$0.11-0.16** |

### Cost optimization tricks
- Skim cheap (search descriptions) before extracting (full article)
- The editorial JSON is compact — cheap to generate, cheap to render
- Python pipeline uses zero LLM tokens
- No wasted sections generating filler content
---

## Implementation steps

### Phase 1: Codex refactors the Python pipeline (ready to go)

The prompt at `codex-restructure-prompt.txt` tells Codex exactly what to do:

1. Add `--editorial-json` CLI mode to build.py
2. Remove all content generation from the Python code — it becomes a pure renderer
3. Strip all static/filler sections from the HTML template
4. Add action tag rendering (Adopt/Try/Track/Note) with semantic colors
5. Keep the dark/amber visual system, top rail, footrail, metadata footer
6. Remove rank.py/gather.py complexity (kept as utilities, no longer in pipeline)
7. Update tests for the new editorial JSON schema

**Codex does the implementation. I verify the output, run tests, commit.**

### Phase 2: Update the cron prompt

Replace the current cron prompt with a self-contained one that:

1. **Contains Alex's profile** — baked directly into the prompt:
   - Building Hermes Agent (custom skills, plugins, gateway, cron)
   - Nanobot-inspired patterns (trust reports, workflow records, delegation discipline)
   - AI agent development broadly (frameworks, models, tools, infrastructure)
   - Interests: MCP, agent-to-agent protocols, local inference, evaluation, voice/vision
   - Currently using gpt-5.5 for coding via Codex, various models for research
   - Legal/AI coverage is low priority right now

2. **Follows the sweep → skim → extract → curate → write editorial JSON → render pipeline**

3. **Outputs editorial JSON** to a known path, then runs the Python renderer

### Phase 3: Configure cron delivery

- Schedule: `30 13 * * *` (6:30 AM PT)
- Skills: `personalized-html-briefings` (for the editorial curation skill, if created)
- Enabled toolsets: `[web, terminal, file]`
- Delivery: HTML attachment to Telegram home channel
- Per-job model override: gpt-5.4 (current session model)

### Phase 4: Test and iterate

1. Run the cron job immediately after setup to verify the first real brief
2. Tune the cron prompt's voice, queries, and tag distribution based on what feels useful
3. Adjust the template if any layout issues appear with real content

## What stays the same
- Dark/amber visual system
- Top rail + footrail
- Issue metadata footer
- Mobile-openable HTML
- Telegram delivery at 6:30 AM PT
- Python pipeline for rendering (but simplified)

## What goes away
- Keyword scoring (rank.py, gather.py complexity)
- Static template sections (image treatment, visual rules, delivery path)
- Template-generated filler content
- Generic news summaries with no personal take
- href="#" dead links
- 40% page wasted on same-copy-every-day text
