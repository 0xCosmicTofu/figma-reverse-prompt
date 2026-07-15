# Extracting & cleaning assets

The goal: every icon/logo/illustration becomes an **import-ready SVG** (or tiny PNG) that
`figma.createNodeFromSvg(str)` imports cleanly, and that inlines into the PROMPT so it's self-contained.

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

Inline each asset in an `ASSET LIBRARY` section as a fenced ```svg block. To also populate the project's
`assets/` folder **without re-transcribing** (which costs tokens twice), write the PROMPT first, then
parse the SVGs back out of it with a small script:
```python
import re
md = open("PROMPT.md").read()
for m in re.finditer(r'\*\*([a-z_]+)\*\*[^\n]*\n```svg\n(<svg.*?</svg>)\n```', md, re.S):
    open(f"assets/icons/{m.group(1)}.svg","w").write(m.group(2))
```
So each asset is transcribed exactly once (into the PROMPT), then extracted to files for free.

## Fonts

Note the source's fonts and whether they're freely available. Keep them if so (e.g. Geist + Inter are
free); otherwise substitute (e.g. Inter) and record the swap in `NOTES.md`. The target Figma must have
them installed, or `loadFontAsync` fails — build a small font-picker helper that tries the intended font
and falls back gracefully.
