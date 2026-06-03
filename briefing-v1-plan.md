# Personalized Morning AI Brief — V1 Plan

## Ranked delivery architecture options

### 1) Hosted HTML page + Telegram link (recommended)
**How it works**
- A scheduled Hermes cron job gathers news and recent-user-interest context each morning.
- It renders a polished HTML artifact for that day.
- The artifact is published to a stable hosting target.
- Hermes sends a Telegram message with a short summary and a direct link.

**Why this is best**
- Best mobile experience.
- Preserves the full visual design of the HTML artifact.
- Easy to archive and revisit.
- Future-friendly for search, tags, weekly recaps, and topic pages.

**Good hosting targets**
- Cloudflare Pages
- Netlify
- GitHub Pages

**Tradeoffs**
- Requires a one-time hosting setup.
- If private access is desired, we may need lightweight auth or an unlisted URL strategy.

### 2) Telegram summary + attached HTML or PDF artifact
**How it works**
- Hermes generates the daily artifact locally.
- Hermes sends a short Telegram message plus the artifact as an attachment.

**Why it is good**
- No hosting required.
- Fastest path to daily use.
- Keeps delivery entirely inside Telegram.

**Tradeoffs**
- HTML file opening behavior on mobile can be awkward.
- PDF is reliable but less dynamic.
- Harder to build a polished archive and permalink system.

### 3) Email-first HTML newsletter
**How it works**
- Hermes generates HTML suitable for email.
- Hermes sends it to a dedicated address each morning.

**Why it is good**
- Familiar newsletter workflow.
- Searchable and archive-friendly.
- Can coexist with Telegram.

**Tradeoffs**
- Email client rendering is more constrained.
- Less immediate than Telegram.
- More friction for iterative feedback.

## Recommendation
Build toward **hosted HTML + Telegram link** as the primary experience.
Use **Telegram attachment/PDF fallback** while hosting is being set up.

---

## V1 system design

### Goal
Deliver a daily, adaptive, elegant morning briefing that reflects both the broader AI ecosystem and the user's changing interests over time.

### V1 components
1. **Source collection layer**
   - AI news and release notes
   - agent/tooling sources
   - dev tooling sources
   - selected topic-specific feeds based on current interest weights

2. **Interest model**
   - Long-term interests: stable themes such as Hermes, agents, builder workflows, dev tooling.
   - Recent-interest boosts: topics that appear frequently in recent conversations.
   - Decay: topics cool down when they stop appearing.

3. **Selection and scoring layer**
   Each candidate item gets a score from:
   - relevance to stable interests
   - relevance to recent momentum
   - practical usefulness for a builder
   - novelty and importance
   - duplication suppression

4. **Editorial layer**
   Generates:
   - a one-line theme for the day
   - top signals
   - why-it-matters-for-you commentary
   - action posture labels: Track / Test / Use / Ignore
   - a rising-topic module when recent interests spike
   - one suggested move for the day

5. **Render layer**
   Outputs:
   - a mobile-first HTML artifact
   - optional preview image
   - optional PDF export later

6. **Delivery layer**
   Sends:
   - Telegram message with summary + direct link
   - fallback attachment if hosting is not available yet

---

## Proposed daily structure

1. **Header / theme**
   - date
   - concise one-line framing

2. **Top signals**
   - 3 high-priority items
   - each includes summary, why it matters, and action posture

3. **For your build journey**
   - items filtered specifically for practical use

4. **Agent / Hermes radar**
   - orchestration
   - memory
   - browser/tool-use reliability
   - evals
   - model/provider changes

5. **Rising topic this week**
   - dynamically filled from recent conversations
   - examples: video gen, evals, ComfyUI, local inference, voice, MCP

6. **One thing to learn**
   - concept / repo / paper / technique

7. **One suggested move**
   - a concrete next action tailored to current interests

8. **Link vault**
   - limited set of high-signal links

---

## Personalization model (V1)

### Stable interest weights
Examples:
- Hermes: high
- agents: high
- dev tooling: high
- product-building: medium-high

### Recent-interest weights
Derived from:
- recent conversation topics
- explicit user requests
- follow-up depth on a topic

### Decay rule
- If a topic stops appearing, its recent-interest score gradually drops.
- Stable interests remain unless explicitly deprioritized.

### Effect on output
These weights affect:
- source selection
- which items make the cut
- section prominence
- suggested experiments and learning modules

---

## MVP rollout path

### Phase 1
- Finalize content structure and visual language.
- Create mockup artifact.
- Confirm delivery preference and hosting path.

### Phase 2
- Implement a cron-driven generator.
- Deliver daily to Telegram with attachment or link.

### Phase 3
- Add hosted archive and stable URLs.
- Add preview image and weekly recap.
- Improve adaptive topic weighting based on more history.

---

## Immediate next implementation recommendation
1. Approve the visual and structural mockup.
2. Choose hosting path: Cloudflare Pages, Netlify, or GitHub Pages.
3. Build the first automated pipeline with Telegram delivery.
4. Run it daily and refine based on use.
