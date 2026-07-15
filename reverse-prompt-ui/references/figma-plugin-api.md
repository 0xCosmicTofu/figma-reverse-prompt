# Figma Plugin-API gotchas (read before any build)

Hard-won from real builds. These prevent the most common failures when constructing a design via a
write-capable Figma MCP (`figma_execute`). Skim all of it once; it's short and every item has bitten a
real build.

## Sizing & Auto Layout

1. **The 100px default-height trap.** `figma.createFrame()` starts at 100×100. When you then set
   `layoutMode = "HORIZONTAL"`, the counter axis (height) stays `counterAxisSizingMode = "FIXED"` at
   100 — so any row (nav item, header, toolbar) silently locks to 100px tall and overlaps its neighbours.
   **Fix:** in your frame-creation helper, immediately after setting `layoutMode`, set BOTH
   `primaryAxisSizingMode = "AUTO"` and `counterAxisSizingMode = "AUTO"` (hug) as the default, then
   override with FIXED/FILL only where the spec calls for it. This one fix eliminates most layout bugs.

2. **Size after append.** Set `layoutSizingHorizontal` / `layoutSizingVertical` = `"FILL"`/`"FIXED"`
   **only after** appending the node to its auto-layout parent — they throw if the parent isn't
   auto-layout yet. Order: create → set children → `appendChild` → then size.

3. **Fill to match a sibling.** When a column must match a fixed-height neighbour (e.g. a stat stack
   matching a map card), give the column `layoutSizingVertical:"FILL"` and each child `layoutGrow:1` —
   do NOT let them hug, or the column falls short. (Content-hug only *coincidentally* matches when fonts
   line up; it breaks under a font swap.)

4. **Bottom-anchor a group:** `layoutGrow:1` + `primaryAxisAlignItems:"MAX"` inside a FIXED-height
   parent (e.g. sidebar footer nav, or a spacer that pushes a tab bar down).

4a. **`SPACE_BETWEEN` needs a FILL-width row to do anything.** A row that HUGS its content has no slack to
    distribute, so items bunch to the left even with `primaryAxisAlignItems:"SPACE_BETWEEN"`. Set the row's
    `layoutSizingHorizontal:"FILL"` so it spans its parent — then space-between actually pushes items to the
    edges (label ⟷ pills, tag ⟷ amount, `--` ⟷ `--`). Easy to miss and a very visible fidelity bug.

4b. **Don't hand-truncate inlined asset paths to fit a build call.** A shortened SVG path renders as a
    malformed blob (e.g. a coin becomes a gradient smear). Inline the full asset, or clone the source node.

## Fills & effects — what writes and what doesn't

5. **`PATTERN` fills and `NOISE` effects can be READ but not WRITTEN** by (at least) the figma-console
   bridge — the `fills`/`effects` setter validates against an older schema that only accepts
   `SOLID` / `GRADIENT_*` / `IMAGE` / `VIDEO` (fills) and rejects `type:"PATTERN"` / `type:"NOISE"`.
   When the source uses one:
   - Document the **native** method in the PROMPT (the correct, editable representation + exact params).
   - Provide a **raster fallback**: for a dot-grid/texture, bake a tiny tile PNG and apply it as a tiled
     `IMAGE` fill (`scaleMode:"TILE"`, tune `scalingFactor` + `opacity`). Note it's a raster approximation.
   - In a live test-build you literally can't set it — leave it honest (flat) rather than faking, and say so.

6. **Gradients and most effects DO write.** `GRADIENT_RADIAL` / `GRADIENT_LINEAR` fills, and `GLASS`,
   `DROP_SHADOW` (including multi-layer stacks), and blur effects all set fine via `node.fills = [...]`
   / `node.effects = [...]`. Reproduce them exactly by reading the source paint/effect and copying its
   values (stops, `gradientTransform`, and for GLASS: `radius`/`lightIntensity`/`lightAngle`/
   `refraction`/`depth`/`dispersion`).

7. **Whose fill is it? — don't approximate a glow with a separate element.** A glow/gradient/texture
   usually belongs to a *specific element's own fill* (e.g. a navbar's radial glow lives in the navbar's
   fill, not a background ellipse). Read which node actually owns it and apply it *there*. Approximating
   it as a separate overlay/ellipse looks close but is wrong and gets flagged. When the user says
   something's "on the wrong element" or "missing," inspect the source node's real `fills`/`effects` and
   match them.

## Reading the source accurately

8. **Read exact properties before matching.** For anything subtle — gradients, effects, per-edge stroke
   weights, opacities — read the source node's actual property values via `figma_execute` and copy them,
   rather than eyeballing from a screenshot. E.g. a corner bracket that looks like an "L" may have a
   stroke on only its two adjacent edges (`strokeTopWeight`/`strokeLeftWeight` = 1, others 0) — read it,
   don't guess, or you'll add stray borders.

9. **Serializing reads:** returning nodes/`figma.mixed` from `figma_execute` throws "Cannot unwrap
   symbol." Build a plain object of primitives (or `JSON.stringify(obj, (k,v)=> typeof v==='symbol' ?
   'MIXED' : v)`) and return that.

## Environment

10. **The plugin sandbox can't `fetch` localhost** (Figma runs plugin code in an https context →
    mixed-content block; even CORS-enabled localhost fails). Don't try to serve assets to the plugin —
    inline the bytes/base64 directly into the build call, or clone existing nodes.

11. **`exportAsync` is slow over the bridge** — batch it (≤6 nodes per `figma_execute` call; ~17 at once
    times out around 30s). See `asset-extraction.md`.

12. **Place the build BESIDE the source, in a named Section — never in random space or on top of work.**
    Read the source frame's `x`/`y`/`width` and target `(source.x + source.width + ~150, source.y)` so the
    replica sits tidily next to its original, tops aligned. Before placing, scan `figma.currentPage.children`
    for any frame whose bounds intersect the target rect; if occupied, shift down or further right. A big
    random `x` offset "works" but scatters replicas and risks landing on other content — align to the source.
    - **Section auto-fit trap:** a `SECTION` auto-fits its contents. If you `appendChild(frame)` and *then*
      set `section.x/y` or `resizeWithoutConstraints`, the section reflows and the **frame can land far from
      where you intended** (seen: a frame ~1900px below target). What matters is the frame's *absolute*
      position. Reliable recipe: build the frame → create the section → `appendChild(frame)` → then set the
      **section** position so the frame's absolute top-left hits target: `section.x = targetX - frame.x`,
      `section.y = targetY - frame.y` (frame.x/y are its coords relative to the section). **Verify** with
      `frame.absoluteBoundingBox` afterward — don't assume.
