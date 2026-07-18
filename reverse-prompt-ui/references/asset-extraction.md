# Extracting & cleaning assets

The goal: every icon/logo/illustration becomes an **import-ready SVG** (or tiny PNG) that
`figma.createNodeFromSvg(str)` imports cleanly, and that inlines into the PROMPT so it's self-contained.

Where the assets come from depends on the extraction mode: **Figma** → `exportAsync` (below);
**live URL** → pull inline SVGs out of the DOM (`el.outerHTML`) — real vectors, no tracing;
**image/screenshot** → you can't extract vectors from pixels, so **match them to an icon library**.

## Icons from a library (default: Phosphor)

**Never trace an icon from a raster.** Most modern UIs use a standard set — identify the icon and fetch
the real vector. **Default to [Phosphor](https://github.com/phosphor-icons/core)** (MIT, ~1,500 icons, 6
weights, and every icon is a plain file in a public repo, so it's trivially fetchable). It's also simply
the most common set in the wild — it was the icon set in every project this skill has been used on.

**Raw URLs** (verified):
```
regular:              .../assets/regular/<name>.svg          e.g. arrows-clockwise.svg
other weights:        .../assets/<weight>/<name>-<weight>.svg  e.g. fill/wallet-fill.svg
weights:              thin · light · regular · bold · fill · duotone
base: https://raw.githubusercontent.com/phosphor-icons/core/main
```
```bash
curl -s https://raw.githubusercontent.com/phosphor-icons/core/main/assets/regular/wallet.svg
curl -s https://raw.githubusercontent.com/phosphor-icons/core/main/assets/fill/wallet-fill.svg
```
Browse/search names at phosphoricons.com. Match by shape *and* weight — a filled vs regular icon reads
very differently; zoom into the screenshot and compare stroke weight before committing.

**Two mandatory fixes before use** (Phosphor's files aren't drop-in):
1. **`fill="currentColor"` → a hardcoded hex.** Figma's SVG importer does NOT resolve `currentColor` —
   the icon lands black or invisible. Replace it with the colour you sampled from the design.
2. **`viewBox="0 0 256 256"` → resize.** Every Phosphor icon is 256-unit; `resize(20,20)` (or whatever
   the design uses) after `createNodeFromSvg`.

```js
const svg = raw.replace(/currentColor/g, "#0F1319");   // sampled colour
const node = figma.createNodeFromSvg(svg); node.resize(24, 24);
```

**Other sets** if the shapes clearly aren't Phosphor: Lucide/Feather (thin, rounded, 24-unit), Heroicons
(Tailwind projects), Material Symbols, Radix. Same pattern: fetch the real file, hardcode the colour,
resize.

## Brand logos from a screenshot

Recovering *brand* marks (companies, tokens) from pixels is the thing mode C looks impossible for. It
isn't — three fetchable registries cover essentially everything. Try in this order:

```
svgl            raw.githubusercontent.com/pheralb/svgl/main/static/library/<slug>.svg    full colour
vectorlogo.zone www.vectorlogo.zone/logos/<b>/<b>-icon.svg                               full colour
simple-icons    raw.githubusercontent.com/simple-icons/simple-icons/develop/icons/<slug>.svg  MONOchrome
```
**simple-icons is a last resort** — it's monochrome-only *and* has **removed** several major marks over
trademark requests (Slack, OpenAI, Salesforce, HubSpot are all gone). Measured on a real 12-logo
dashboard: 11/12 came back as real full-colour marks; only one was monochrome-only.

**Never trace a logo.** But "fetch the official SVG" is necessary, **not sufficient** — registry logos are
built for the *web*, where `currentColor`, CSS classes, and SVG filters all work. **Figma's importer
resolves none of them.** Budget a **normalization pass** on every logo; all of these are real, observed
failures:

- **Wrong variant.** Many registries ship the *white-on-dark* version (`fill="#ffff"`) → invisible on a
  light tile. Check the variant against the tile colour you're placing it on.
- **Filters / masks.** `<mask>` + `feGaussianBlur` (e.g. Google's marks) are **dropped** by the importer
  and the logo renders wrong. Flatten to the plain path(s).
- **Wordmark lockups.** svgl often ships `icon + wordmark` (a 999×699 box). At ~20px it reads as a squished
  smudge. Drop the wordmark paths, keep the mark.
- **`viewBox` crops.** A wordmark SVG whose `viewBox` crops to the icon works — **but** the icon may be a
  **subpath at the tail of a glyph path**, not its own `<path>`. A path-level regex then silently matches
  nothing. Extract the subpath.
- **XML prologs, editor comments, `<style>` classes.** Illustrator exports carry all three; the importer
  wants a bare `<svg>` with inline fills. Strip the prolog, inline the class fill.
- **No `fill` at all.** simple-icons marks inherit `currentColor` → they land black unless tinted.

**Assert before you inline:** every asset should start with `<svg` and contain no `currentColor` / `var(`.
A three-line check catches most of the above before it reaches the build.

**Logo *tiles* are usually per-brand, not uniform.** A card grid of integrations rarely puts every logo
on the same light square. The common pattern: brands with a strong brand colour get a **solid branded
tile with a contrasting (often white) logo** — HubSpot on orange, Slack on charcoal, Mailchimp on yellow
— while the rest get a **light neutral tile with their own full-colour logo**. Don't default the whole
grid to light tiles; read each tile's fill off the source and recolour the logo to contrast where the
tile is branded. This is a colour call, so it's exactly the kind of thing a **crop-and-zoom overlay**
(below) exists to catch.

## From a live URL (mode B)

A shipped site gives you *measured* values, not guesses — treat it as nearly Figma-grade. In the browser:

```js
// exact tokens off a real element
const s = getComputedStyle(el);
({ color: s.color, bg: s.backgroundColor, font: s.fontFamily, size: s.fontSize,
   weight: s.fontWeight, pad: s.padding, gap: s.gap, radius: s.borderRadius,
   shadow: s.boxShadow, border: s.border });
el.getBoundingClientRect();                    // real geometry
// real vectors — no tracing
[...document.querySelectorAll('svg')].map(s => s.outerHTML);
```
Notes: computed colours come back as `rgb()/rgba()` → convert to hex + opacity. Icons may be inline
`<svg>` (grab directly), a `<use href="#id">` sprite (grab the referenced `<symbol>`), an `<img src>`
(fetch it), or a CSS background/icon font (fall back to library matching, above). Grab the real font
stack from `fontFamily` rather than eyeballing it.

## Getting the SVGs out of Figma

Two sources, in order of preference:

1. **The MCP asset server** (`get_design_context` returns `http://localhost:3845/assets/<hash>.svg`
   URLs). Bulk-download with `curl`. Fast when it works.

2. **`exportAsync` fallback — use when the asset server 500s** ("Error getting image"). Export each node
   via the write-capable bridge:
   ```js
   const n = await figma.getNodeByIdAsync(id);
   const bytes = await n.exportAsync({ format: "SVG" });
   let s = ""; for (let i=0;i<bytes.length;i++) s += String.fromCharCode(bytes[i]);
   return s;
   ```
   **Batch it: ≤6 nodes per `figma_execute` call** — a single call exporting ~17 icons times out (~30s).
   Bonus: `exportAsync` output already has real hex (no CSS `var()`), so it needs less cleaning.

   **Export gotchas:**
   - `getNodeByIdAsync` **cannot resolve instance-internal IDs** (the `I<id>;<id>;…` form for sublayers of
     an instance) — it returns `null`. Traverse from a stable ancestor to get the node *reference*, and call
     `.exportAsync()` on that reference (don't round-trip through the composite ID).
   - **Hidden component variants won't export** → `"Failed to export node. This node may not have any
     visible layers."` Token/brand components often carry hidden states. Export a *visible* instance, or
     recreate the mark (e.g. reuse a logo you already have as a placeholder — the source is often a
     placeholder too).
   - **Stale bridge:** if heavy ops (`exportAsync`, `fillGeometry`/`strokeGeometry`) keep dropping the
     connection while trivial reads succeed, the websocket may have gone stale (e.g. left open overnight).
     Ask the user to **reload the Figma file + restart the bridge** before assuming your node IDs or
     approach are wrong. Reloading regenerates instance-internal IDs, so re-resolve them by traversal.

## Cleaning

- **Strip CSS variables → hardcoded hex.** Figma's SVG importer chokes on `fill="var(--fill-0, #0017AF)"`
  and renders black. Replace with the literal: `fill="#0017AF"`. (asset-server SVGs need this; exportAsync
  output usually doesn't.)
- **Flatten multi-part icons to a single 20×20 `<g transform>` SVG.** Figma often exports an icon as
  several separately-positioned `<svg x y width height viewBox>` fragments. The importer positions
  *nested* `<svg>` unreliably. Convert each fragment to `<g transform="translate(x y) scale(w/vw h/vh)">…</g>`
  inside one `<svg viewBox="0 0 20 20">`. Verify by rendering the flattened icons in a browser (or
  building them) before trusting them.
- Keep multi-color brand logos (gradients, clip paths) as-is — they import fine.
- Preserve each element's own colors from context (an icon that's lime in the design exports lime; an
  inactive tab icon exports at its real opacity). Don't recolor unless the spec says to.

## Simplifying heavy vectors (maps, detailed illustrations)

A detailed world map can be ~1.5 MB — far too big to inline. But such art is usually **pure polygons**
(only `M`/`L`/`H`/`V`/`Z`, no curves), which compresses enormously:

- **Douglas-Peucker** vertex reduction (drop points that don't change the silhouette beyond tolerance ε)
  **+ integer coordinates** (round away sub-pixel decimals).
- Measured result on a real world map: **1.5 MB → ~48 KB (~3%)** at ε=2, visually identical at card
  scale; ~85 KB at ε=1 is pixel-identical. Sweep ε and **render each candidate at the actual display
  size** to pick the smallest that still reads.
- Also worth dropping: tiny sub-paths (islands) below an area threshold; they're invisible at UI scale.
- Cropping to the visible region rarely helps much if the art is offset to fill the frame — measure
  before bothering.

## Repeating textures (dot grids, noise)

If the source uses a native `PATTERN` fill (which the bridge can't write — see figma-plugin-api.md #5),
bake a **tiny tile PNG** (e.g. a 16×16 transparent tile with one small dot, ~100 bytes → ~130 base64
chars) and apply it as a tiled `IMAGE` fill (`scaleMode:"TILE"`, tune `scalingFactor` for spacing and
`opacity` for subtlety). Inline the base64 in the PROMPT. Document it as a raster approximation of the
native pattern, and give the native params too so a capable target can do it properly.

## Inlining into PROMPT.md — and saving the asset files cheaply

Inline each asset in an `ASSET LIBRARY` section as a fenced ```svg block. The rule is **transcribe each
asset exactly once**; which direction you go depends on where the assets came from.

**Assets came from Figma (mode A/B)** → write the PROMPT first, then parse the SVGs back out of it into
`assets/` with a small script:
```python
import re
md = open("PROMPT.md").read()
for m in re.finditer(r'\*\*([a-z_]+)\*\*[^\n]*\n```svg\n(<svg.*?</svg>)\n```', md, re.S):
    open(f"assets/icons/{m.group(1)}.svg","w").write(m.group(2))
```
So each asset is transcribed exactly once (into the PROMPT), then extracted to files for free.

**Assets came from a library/registry (mode C)** → **invert it.** The files already exist on disk from the
fetch, so hand-write the spec sections and have a script **append** the ASSET LIBRARY *from* `assets/`:
```python
out = []
for n in ICONS:
    out.append(f"**{n}**\n```svg\n{open(f'assets/icons/{n}.svg').read().strip()}\n```\n")
open("PROMPT.md","a").write("\n".join(out))
```
Same principle, opposite direction — and it means your normalization fixes (see "Brand logos" above) live
in the files *and* the prompt, rather than only in the build call where they'd be lost.

## Fonts

Note the source's fonts and whether they're freely available. Keep them if so (e.g. Geist + Inter are
free); otherwise substitute (e.g. Inter) and record the swap in `NOTES.md`. The target Figma must have
them installed, or `loadFontAsync` fails — build a small font-picker helper that tries the intended font
and falls back gracefully.
