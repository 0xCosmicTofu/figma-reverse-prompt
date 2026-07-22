# Restyling a recreation — with WCAG enforced

An optional pass **after** the 1:1 rebuild: keep the structure, swap the style, and prove the result meets
WCAG. Only do this when the user asks for a re-theme/recolour — the faithful recreation comes first.

The whole thing works because a reverse prompt already separates **structure** (layout tree, geometry,
component roles) from **style** (token values). A restyle swaps the style layer while the structure holds.

## 1. Make the token layer semantic first

A restyle is only possible if every colour references a **role**, never a literal. Roles worth having:

```
page · surface · surface-subtle · surface-raised · border · border-strong
text-primary · text-secondary · text-muted · text-disabled
accent · on-accent · status-{success,warning,danger,info,neutral} + their bg/on pairs
```

**Watch for overloaded hexes.** The same literal often serves several roles — in one build `#18181B` was
*text-primary*, the *primary-CTA fill*, AND the *logo chip*. A hex→hex remap cannot disambiguate those;
you need the role, inferred from node type + name + ancestry. Getting this wrong sends all three to the
same colour. (This is the strongest argument for binding roles at build time.)

## 2. Generate the new palette, then REPAIR it against contrast

Use `wcag_contrast.py`. Declare the pairs that co-occur, compute each ratio, and repair failures by moving
the foreground's **OKLCH lightness** (hue/chroma preserved, so brand hue survives). Two levers in order:
foreground first; if it is already at an extreme and still fails, repair the **background**.

Targets — **AA**: 4.5 text · 3.0 large text (≥24px, or ≥18.66px bold) · 3.0 non-text (1.4.11).
**AAA**: 7.0 / 4.5.

Expect the loop to surface genuine design decisions rather than silently "fixing" things:
- A mid-saturation CTA fill (e.g. amber) often **cannot** carry AA text as black *or* white. Resolution:
  deepen the fill and use light text, or lighten it and use dark text. That is a design call the loop
  forces into the open.
- A vivid brand colour used as *body text* rarely reaches 4.5:1 on a light surface. Keep two tokens:
  `accent` (fills, large text) and `accent-text` (darkened, for body).
- **Strict 1.4.11 has an aesthetic cost.** Near-invisible hairline borders must brighten to 3:1, which
  reads as more "outlined" than typical dark themes. Flag this trade — the alternative is to separate
  panels by fill instead of borders and drop the borders entirely.

## 3. Audit the ARTIFACT, not the palette — this is the step that matters

**A compliant palette does not mean a compliant frame.** On a real run the palette passed 23/23 while the
built frame still had **10 failing text pairs**, because:
- unmapped colours survived the remap (`#3F3F46` sidebar labels sat at **1.71:1**), and
- the declared pair list **missed backgrounds that actually occur** — muted text was checked on `surface`
  but really also lands on `surface-raised` (3.59:1) and `surface-subtle` (4.09:1).

So walk the real tree. For every visible TEXT node, resolve its **effective background** (nearest ancestor
with a visible opaque SOLID fill), compute the ratio, and flag failures. Repeat for VECTOR/ELLIPSE fills
and strokes at 3.0. Then auto-repair each failing node against *its own* background and re-audit until
zero. Sketch:

```js
function solidFill(n){ /* last visible SOLID fill with opacity>0.9 -> hex */ }
function effBg(n){ let p=n.parent; while(p){ const c=solidFill(p); if(c) return c; p=p.parent; } }
const large = size>=24 || (/Bold|Semi/i.test(style) && size>=18.66);
const need  = large ? 3.0 : 4.5;              // non-text: 3.0
// repair in HSL (hue-preserving) by binary-searching lightness until ratio>=need
```
Report `pass/fail` counts plus every failing pair. **The verdict is the audit, not the palette.**

## 4. What you can and cannot claim

Say **"WCAG 2.1 AA contrast-verified"**, not "WCAG compliant":
- Enforced and provable here: **1.4.3** (contrast minimum) and **1.4.11** (non-text contrast).
- Checkable by inspection: **1.4.1** (don't rely on colour alone) — e.g. status chips must keep text
  labels, not just hue.
- Out of scope for a static Figma frame: focus order, keyboard operation, resize/reflow, ARIA. Those live
  in markup and interaction. Don't imply coverage you can't demonstrate.
- **Disabled/inactive elements are exempt** from 1.4.3. Decide deliberately: either mark them exempt and
  document it, or lift them to pass and accept that the "disabled" affordance weakens.

## 5. Verification metric for a restyle

There is no reference image to diff against, so the metric changes to two numbers:
1. **Structural identity** to the recreation — only colours moved, so geometry should be unchanged.
2. **The audit** — `N/N` text and non-text pairs at target.

Build the restyle on a **clone**, never on the original recreation, and place it beside it.
