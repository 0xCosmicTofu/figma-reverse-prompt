# Themes as Figma variables + modes

The **preferred** way to ship a restyle. One frame, roles as variables, each theme a **mode** — switching
is a toggle, not a duplicate frame. Supersedes recolouring a clone (which doubles the nodes and drifts the
moment the layout changes).

## Build it

```js
const col   = figma.variables.createVariableCollection("Theme");
const light = col.modes[0].modeId;  col.renameMode(light, "Light");
const dark  = col.addMode("Dark");

let v;                                    // signature differs across API versions
try   { v = figma.variables.createVariable(name, col,    "COLOR"); }
catch { v = figma.variables.createVariable(name, col.id, "COLOR"); }
v.setValueForMode(light, {r,g,b});        // 0..1, NOT 0..255
v.setValueForMode(dark,  {r,g,b});

// bind — returns a NEW paint, so reassign the array
node.fills = node.fills.map(f =>
  f.type === "SOLID" ? figma.variables.setBoundVariableForPaint(f, "color", v) : f);

frame.setExplicitVariableModeForCollection(col, dark);   // flip the whole frame
```

Name roles with slashes (`surface/default`, `text/muted`, `status/prod-bg`) — Figma groups them into
folders in the UI.

## Reading a bound colour (the audit gotcha)

`paint.color` still holds the **stored** value, not the resolved one. Any contrast audit must follow the
binding for the mode being audited, or it silently checks the wrong colours:

```js
function paintHex(p, modeId) {
  const bv = p.boundVariables && p.boundVariables.color;
  if (bv && bv.id) {
    const val = varsById[bv.id].valuesByMode[modeId];   // resolve for THIS mode
    if (val && typeof val.r === "number") return rgbToHex(val);
  }
  return p.color ? rgbToHex(p.color) : null;
}
```

## Overloaded literals are the main hazard

One hex routinely serves several roles, and binding by hex alone silently merges them. On a real run
`#18181B` was **three** roles — `text/primary`, `cta/fill`, and the logo chip `mark/bg` — and the first
pass bound six *icons* to `mark/bg`, which turned them near-invisible in dark mode. `#FFFFFF` was
similarly `surface/default`, `surface/raised`, and `cta/on`.

Disambiguate by **node type + name + ancestry**, and remember:
- a **VECTOR is an icon** — never a chip or a button fill,
- a **FRAME fill** is a surface/chip,
- a **TEXT fill** is a text role,
- an icon inside a coloured button takes the button's `on-` role, not a surface role.

After binding, list any unbound colours and check them — leftovers are usually icon vectors.

## Never repair a surface as if it were a foreground

An auto-repair loop that lightens/darkens "foregrounds" will happily drive `surface/default` to `#000000`
because some white icon is bound to it. **Exclude background roles** from foreground repair:

```js
const isBg = n => /^surface\//.test(n) || /-bg$/.test(n) || n==="cta/fill" || n==="amber/fill" || n==="mark/bg";
```

## Modes make the accessibility trade-off disappear

The killer finding: after binding a faithful recreation, the audit reported

| mode | text | non-text |
|---|---|---|
| **Light** (faithful) | 54/88 | 33/50 |
| **Light AA** (repaired) | **88/88** | **50/50** |
| **Dark** (repaired) | **88/88** | **50/50** |

**The faithful reproduction fails AA because the original design does** (`#A9A9AE` on white is 2.34:1 in
the source). That is not a bug in the rebuild — it is a true finding about the source, and worth reporting
to the user as such.

With a clone you would have to *choose*: faithful **or** accessible. With modes you ship **both** —
`Light` preserves the source exactly, `Light AA` is the same layout with repaired token values, `Dark` is
the re-theme. One frame, three truths, and the diff between `Light` and `Light AA` is itself a useful
accessibility report on the original design.

Repair per **role against its worst-case background** (a role lands on several surfaces), then re-audit
every mode — never assume a value that passes on one surface passes on all of them.
