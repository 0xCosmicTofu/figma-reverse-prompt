---
name: reverse-prompt-ui
description: >-
  Reverse-engineer an existing UI (a Figma frame/node, a screenshot, or a live site) into a
  SELF-CONTAINED "reverse prompt" — a single PROMPT.md that another agent can follow to rebuild the
  design 1:1 in Figma, with every asset inlined. Use this whenever the user wants to "reverse prompt",
  "make a prompt for this UI/screen/design", "turn this Figma into a prompt", "recreate this in Figma",
  "capture this screen as a rebuild prompt", or points at a Figma node / screenshot and asks for a
  prompt that reproduces it. Also use to add another screen to an existing reverse-prompts project.
  Handles the whole loop: extract → clean & inline assets → author the prompt → test-build it live in
  Figma → screenshot-compare → log deltas. ALSO handles restyling a recreation — "recreate this but in
  dark mode", "apply our brand colours to it", "re-theme this screen" — generating a new palette that is
  WCAG-contrast-repaired and auditing the built frame node-by-node until it passes AA. Assumes a
  WRITE-capable Figma MCP (one that executes plugin code, e.g. figma-console); the read-only official
  Dev-Mode MCP can't build.
---

# Reverse-prompt a UI

Produce a **self-contained `PROMPT.md`** that rebuilds an existing design 1:1 in Figma. "Self-contained"
= every asset inlined (import-ready SVGs, base64 tiles), exact tokens/spacing, the full layout tree, and
the build gotchas — so a fresh agent with a write-capable Figma MCP can paste it and go, no external
files needed.

Keep projects in a **reverse-prompts hub** folder (e.g. `~/reverse-prompts/`) — each UI is its own
subfolder. If the hub has a top-level `README.md`, read it first (it holds the running project index and
any accumulated learnings), and register the new screen there when done.

## Prerequisites (state these if missing, don't silently fail)
- To **build/test** (any mode): a **write-capable Figma MCP** — one that runs plugin code
  (`figma_execute` / `exportAsync`), e.g. figma-console. The official Figma Dev-Mode MCP is read-only.
- To **extract**: depends on the source — a Figma MCP (mode A), a browser (mode B), or just vision (mode C).
- Fonts the design uses must be **installed in the target Figma**, or note the substitution.

## The method

Work through these in order. Steps 1–3 produce the deliverable; 4–5 verify and file it.

### 1. Extract — pick the mode that matches the source

Whatever the mode, you're after the same things: the **layout tree** and **exact tokens** (colors *with
opacity*, radii, type family/size/weight/spacing, padding/gaps), plus **import-ready assets**. What
differs is how much is *measured* vs *inferred* — be honest about that in the prompt's `## Requires` and
in `NOTES.md`.

| Mode | Source | Fidelity | Tokens | Assets |
|---|---|---|---|---|
| **A. Figma** | a node/frame | **1:1** | exact (incl. variables) | real vectors via `exportAsync` |
| **B. Live URL** | a shipped site/app | **near-1:1** | exact (computed CSS) | real SVGs from the DOM |
| **C. Image** | screenshot / flat PNG | **approximation** | sampled/estimated | matched from an icon library |

**A — Figma (best).** `get_design_context` + a screenshot on the frame and its key sub-frames; note node
IDs, the layout tree, and exact tokens. Read variable/style definitions. Capture effects and gradient
fills by reading the node that actually owns them (`references/figma-plugin-api.md` → "Whose fill is
it?").

**B — Live URL (underrated).** Open it in a browser and read the *computed* values — this is nearly as
good as Figma and needs no file. `getComputedStyle` on the key elements gives exact colors, font family/
size/weight, padding, gaps, radii, shadows; `getBoundingClientRect` gives real geometry. Pull **inline
SVGs straight out of the DOM** (`outerHTML`) — those are real vectors, no tracing. Screenshot for
reference. Prefer this over mode C whenever the design exists at a URL.

**C — Image / screenshot (approximation — say so).** You can still produce a well-structured, close
rebuild, but be upfront that it isn't 1:1:
- **Colors:** sample pixels (script the eyedrop rather than guessing by eye). Flat fills read reliably;
  gradients, opacity, and antialiased edges are estimates.
- **Geometry:** measure against a known anchor (a 44px button, a 16/24px icon, the frame width) and
  derive the spacing scale — real UIs snap to 4/8, so round to the scale rather than reporting 13px.
- **Type:** identify the family by eye and treat it as an **assumption** — name your best guess in
  `## Requires` and say it's inferred.
- **Icons:** do NOT trace. Identify them and pull the **real vectors from an icon library — default to
  Phosphor** (see `references/asset-extraction.md` → "Icons from a library"). Most modern UIs use a
  standard set, so this recovers near-perfect assets from pixels.
- **Brand logos:** fetch the official SVG; never trace.
- Anything genuinely unknowable from pixels (hidden states, exact effect params) — omit it and note it.

**Check EFFECTIVE visibility, not just `node.visible`.** A node can be `visible: true` yet not render
because an *ancestor* is `visible: false` (e.g. an `actions` frame is hidden on one card, but its badge
text nodes are still `visible: true`). If you traverse for text/icons naively you'll extract — and then
render — elements the design hides. Compute effective visibility as `AND` of the node's and every
ancestor's `visible`, and skip anything effectively hidden. Cross-check against the screenshot: if the
screenshot doesn't show it, don't build it. (Two instances of the "same" component often differ only by
which sublayers are toggled off — inspect each, don't assume they're identical.)

### 2. Clean & extract assets
Get every icon/logo/illustration as an import-ready SVG, then simplify. Details and the exportAsync
fallback are in **`references/asset-extraction.md`** — read it before pulling assets. In short: strip CSS
`var()` → hardcoded hex; flatten multi-part icons to a single 20×20 `<g transform>` SVG; Douglas-Peucker
+ integer coords for heavy vectors (maps, illustrations); rasterize repeating textures to a tiny tiled
PNG only as a fallback.

### 3. Author `PROMPT.md`
Structure: **build-notes → design tokens table → layout tree (Auto Layout, sizing modes, per-section
specs) → build order → inline ASSET LIBRARY**. Inline every asset so the prompt is one paste. Write the
layout as a spec (frames, `layoutMode`, FILL/HUG/FIXED, itemSpacing, padding, per-element type/color) —
not code. Note intentional substitutions (e.g. a font swap) explicitly, and tell the target agent to
screenshot-compare and iterate.

**Make the PROMPT truly self-contained — inline the build-time gotchas it needs.** The recipient is a
fresh agent + Figma MCP that may NOT have this skill, so a `PROMPT.md` that links out to
`references/…` for the gotchas is broken when sent alone — they'll hit the 100px trap and build it wrong.
Include a short **"Build notes"** block near the top with the handful of build-time gotchas that apply:
the 100px default-height fix, size-after-append, fill-to-match-a-sibling (if used), and any
PATTERN/NOISE/glow caveat *if the design uses one*. The extraction/`exportAsync`/Douglas-Peucker material
in `references/` is for YOU (the authoring agent) — the recipient doesn't need it, since assets arrive
pre-inlined. Don't dump the whole gotcha list into every prompt; include only what that design exercises.

**Open every PROMPT with a `## Requires (you supply)` section** — the standalone contract, the first
thing the recipient reads (they may run the prompt with no other context). List: (1) a **write-capable
Figma MCP** (the read-only Dev-Mode MCP can't build); (2) the **fonts** that must be installed in the
target Figma (name them, note substitutions); (3) **supplied content** — either "none, every asset is
inlined below," or any raster the prompt can't carry. Big content rasters (hero photos, illustrations)
genuinely can't be inlined — a 1 MB photo is ~270k tokens — so state them as a supplied asset up front
rather than letting the builder discover a placeholder mid-build. Be honest about what "1:1" covers:
layout + vector assets reproduce exactly; supplied photos and installed fonts are prerequisites, not
things the text carries.

### 4. Test-build it live
Build it in the Figma file via the MCP to prove the prompt works. To avoid re-passing large assets into
the build call, **clone the source nodes** — icons, and especially any big raster (a hero photo,
illustration) whose bytes you'd never want to shuttle — into a freshly-built layout. This tests the
layout logic (the hard part) without re-shuttling assets, and the cloned raster/effects come for free.
**Placement — put the build directly BESIDE the source, not in random far-off space:** read the source
frame's `x`/`y`/`width`, target `(source.x + source.width + ~150, source.y)`, and **check that region is
clear of other top-level frames** before dropping it (scan page children for any intersecting the target
rect; shift down/further right if occupied). Wrap it in a clearly-named `Section`, but note **sections
auto-fit and reflow** — set the section's position from the frame's target and then *verify*
`frame.absoluteBoundingBox` actually landed beside the source (details + recipe in
`references/figma-plugin-api.md` #12). This keeps every replica sitting tidily next to its original and
never on top of existing work. Then screenshot the result and compare to the original — look hard,
section by section. **A full-frame eyeball pass is not enough for colour or per-element treatment.** If you
have the source as a raster (mode C, or any time the original image is in the file), do a **crop-and-zoom
overlay**: clone the source image into a `clipsContent` frame sized to a region, offset the clone
(`clone.x = -fx*W`), and screenshot that crop at 1.5×+. Colour differences (a branded vs light tile, a
gray vs white card fill, an icon vs a dot) only become legible zoomed in — a mode-C build that "looked
right" at full frame had five wrong logo-tile colours that only showed under the crop. **And crop the same
band from BOTH — put your reproduction's region directly beside the original's, don't eyeball each alone.**
Differences in a repeated element (all five stat icons identical vs distinct, one count coloured) are
invisible in isolation and obvious side by side.

**MEASURE — don't eyeball. This is the step that actually closes the gap.** Eyeballing (even zoomed) took
four correction rounds on one mode-C screen; measuring found every delta in a single pass on the next.
Export the source and your build **to PNG at the same canvas size** and compare numerically in a script:

```python
# longest run of an element's own fill down a column == its exact height
def longest(a, x0,x1, y0,y1, lo,hi):      # a = grayscale array
    best=(0,None,None)
    for x in range(x0,x1):
        col=a[y0:y1,x]; ok=(col>lo)&(col<hi); s=None
        for i,v in enumerate(ok):
            if v and s is None: s=i
            elif not v and s is not None:
                if i-s>best[0]: best=(i-s, y0+s, y0+i-1)
                s=None
    return best   # (height, top, bottom)
```
Run it on both images for each element whose fill differs from its parent (cards, containers, fields), and
on text-row centres for baselines. Then fix to the numbers. It catches what no overlay shows — e.g. a
sidebar row 2.3px too tall is invisible at full frame but compounds to ~25px of drift by the bottom of the
list. Also report a **global score** (mean-abs-luminance match, plus a **Sobel edge-map** match — the edge
map is what catches thin panel borders that luminance averages away) so you know when to stop.

**NEVER `clone()` + `rescale()` a node that lives in the user's file.** Building an in-canvas overlay by
cloning the source raster and rescaling the clone **corrupted the original** — it was scaled and moved,
twice, even after being restored (the original stayed correctly parented, so it was not a stray
`appendChild`). Do all comparison **outside Figma**: `exportAsync` both nodes to PNG and diff them in a
script. It is more precise *and* it cannot damage the user's artwork. If you must overlay in-canvas,
rasterise the source into a *new* image node first. If you do corrupt something, restore with explicit
`resize()` + re-asserting the `IMAGE/FILL` fill, then **verify with a fresh screenshot**.

**Reproduce the container nesting, not just the visible leaf elements.** The easiest structural miss is
flattening a group of elements that actually sit inside a **panel/card** — because a white panel on a
near-white page is nearly invisible in a flat screenshot; its only cues are a **1px border** and a
**consistent inner gutter** around the group. Before building a content region, ask "is this a flat stack,
or are these groups wrapped in panels?" and trace the border rectangles. A telltale: leaf cards that are
*greyer* than the page (a stat card `#F4F4F5` on a `#F7F7F8` page) usually means they sit inside a **white**
panel — the card-in-card contrast only works with the panel present. Getting the leaf fill right but
omitting its container still looks wrong.

**Don't "upgrade" a repeated placeholder-looking element into distinct semantics.** If a row of stat cards,
list items, or badges all carry the *same* mark in the source, that uniformity is the design — often the
app reusing its own logo mark as a generic icon. Reproduce it as-is. Inventing five distinct semantic icons
(plug/check/chart/…) where the source repeats one mark is a fidelity regression, not an improvement — match
the source, don't out-design it. **The Plugin-API gotchas in
`references/figma-plugin-api.md` are mandatory reading before building** — they prevent the most common
failures (the 100px-height trap, overlaps, glow-on-wrong-element).

### 4b. Optional: restyle it, with WCAG enforced

Only when the user asks for a re-theme/recolour (dark mode, a brand palette) — **the faithful recreation
comes first**. This works because the prompt already separates structure from style: swap the style layer
and the structure holds. Full method in **`references/restyle-accessible.md`**, contrast engine in
**`references/wcag_contrast.py`**. The three-line version:

1. Make the tokens **semantic** (role-based). Beware overloaded hexes — one literal often serves several
   roles (text vs CTA-fill vs logo chip), and a hex→hex remap cannot tell them apart.
2. Generate the new palette, then **repair it against contrast** — move OKLCH lightness (hue preserved)
   until each pair meets AA (4.5 text / 3.0 large & non-text). If a foreground is already at an extreme
   and still fails, repair the **background** instead.
3. **Audit the artifact, not the palette.** A compliant palette does NOT mean a compliant frame — on a real
   run the palette passed 23/23 while the built frame still had 10 failing pairs (unmapped colours
   survived; the declared pairs missed backgrounds that actually occur). Walk the real tree, resolve each
   node's *effective background*, repair per-node, and re-audit until zero.

Build the restyle on a **clone**, beside the recreation. Claim **"WCAG 2.1 AA contrast-verified"** (1.4.3 +
1.4.11) — not "WCAG compliant"; focus order, keyboard and reflow can't be shown in a static frame.

### 5. Log deltas & register
Write a `NOTES.md` recording: the source node ID, screen-specific content, any known deltas from the
original (font swaps, effects the bridge can't write, simplification levels), and any *new* gotcha the
build surfaced. Register the screen in the hub `README.md`. If a correction reveals a **reusable** lesson
(applies to any UI, not just this one), also fold it into the hub README's method/gotchas AND into
`references/figma-plugin-api.md` here — the whole point is that each build makes the next one cleaner.

## Project shape

Pick the lightest structure that fits — don't build the multi-screen scaffold until there's a 2nd screen.

- **One-off screen** → flat folder:
  ```
  <project>/
  ├── PROMPT.md      the self-contained deliverable
  ├── NOTES.md       deltas & fidelity notes
  └── assets/        source assets (icons/, etc.)
  ```
- **Multi-screen product** → a shared core + per-screen folders:
  ```
  <project>/
  ├── README.md
  ├── design-system/   DESIGN-SYSTEM.md (tokens, shared chrome, gotchas) + assets/
  └── screens/<name>/  PROMPT.md + NOTES.md + assets/
  ```
  The `design-system/` is the reusable authoring reference (sidebar, nav, logo, tokens shared across
  screens); each screen's `PROMPT.md` still inlines what it needs so it stays a single paste.

## Conventions
- **Auto Layout everywhere**; absolute positioning only for true overlays (badges, FABs, map pins,
  corner brackets).
- Assets import-ready: hardcoded hex (no CSS vars); icons as 20×20 `<g transform>` SVGs.
- Fidelity is the bar. Test-build and compare; a "looks about right" spec that hasn't been built is not
  done. When the user flags a miss, read the source node's *actual* properties before fixing — match the
  source, don't eyeball.

## References (read when relevant)
- `references/figma-plugin-api.md` — the hard-won Plugin-API gotchas. **Read before any build.**
- `references/asset-extraction.md` — extracting, cleaning, flattening, and simplifying assets.
- `references/restyle-accessible.md` — restyling a recreation with WCAG enforced (step 4b).
- `references/wcag_contrast.py` — contrast math + OKLCH repair (importable).
