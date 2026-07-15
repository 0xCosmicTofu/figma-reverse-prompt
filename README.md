# reverse-prompt-ui

An [agent skill](https://docs.claude.com/en/docs/claude-code/skills) that turns an existing UI — a Figma
frame, a screenshot, or a live site — into a **self-contained "reverse prompt"**: a single `PROMPT.md`
that any coding agent (Claude Code, Codex, …) with a write-capable Figma MCP can follow to rebuild the
design **1:1 in Figma**, with every asset inlined.

It encodes a full method (extract → clean & inline assets → author the prompt → test-build it live and
screenshot-compare → log deltas) plus the hard-won Figma Plugin-API gotchas that make a build land on the
first try instead of the fifth.

## Two roles (important)

- **Authoring** — install this skill; point it at a design; it *produces* a `PROMPT.md`. (Needs read
  access to the source design, e.g. via a Figma MCP.)
- **Consuming** — a `PROMPT.md` is a standalone artifact. Hand it to a fresh agent + a **write-capable
  Figma MCP** and it rebuilds the design. The consumer does **not** need this skill installed — each
  prompt carries its own build notes and inlined assets, and opens with a `## Requires` contract.

So you can share a single `PROMPT.md` on its own, or share this skill so others can generate their own.

## Install

The skill lives in the [`reverse-prompt-ui/`](reverse-prompt-ui/) folder.

**Claude Code** — copy it into your skills directory:
```bash
git clone https://github.com/0xCosmicTofu/figma-reverse-prompt.git
cp -r figma-reverse-prompt/reverse-prompt-ui ~/.claude/skills/
```
(or into a project's `.claude/skills/`). It then triggers automatically, or via `/reverse-prompt-ui`.

**Other agents (Codex, etc.)** — point your agent at `reverse-prompt-ui/SKILL.md`, or copy the folder
into wherever your agent loads skills/instructions from. The skill is plain Markdown — `SKILL.md` is the
entry point; `references/` loads on demand.

## Requirements

- A **write-capable Figma MCP** — one that executes plugin code (e.g.
  [figma-console](https://github.com/tommy-mor/figma-console-mcp)). The read-only official Figma
  Dev-Mode MCP can *read* a design but cannot *build* one.
- The design's **fonts installed** in the target Figma (free fonts like Inter / Geist / Funnel Display).

## Use

Point it at a design and let it run the loop:

> "reverse-prompt this screen" + a Figma node URL
> "make a Figma-rebuild prompt for this" + a screenshot
> "recreate this landing page in Figma" + a URL

It extracts the design, cleans and inlines the assets, writes a `PROMPT.md`, test-builds it in Figma to
verify, and logs any deltas. Each build makes the skill sharper — corrections fold back into
`references/figma-plugin-api.md`.

## What a produced prompt looks like

A `PROMPT.md` contains: a `## Requires` header (write-capable MCP, fonts, any supplied rasters) → build
notes (the Plugin-API gotchas that design needs) → a design-tokens table → the layout tree (Auto Layout,
sizing modes, per-section specs) → an inline **ASSET LIBRARY** with every icon/logo as an import-ready
SVG. Paste it into a coding agent with a Figma MCP and it builds the screen.

> **On fidelity:** layout and vector assets reproduce exactly. Two things a text prompt can't carry —
> **installed fonts** and **large content photos** (a 1 MB hero image ≈ 270k tokens) — are stated as
> prerequisites in the prompt's `## Requires` header, not hidden.

## What's in here

```
reverse-prompt-ui/
├── SKILL.md                        the method, when-to-use, project shapes, conventions
└── references/
    ├── figma-plugin-api.md         the Plugin-API gotchas (read before any build)
    └── asset-extraction.md         extracting / cleaning / flattening / simplifying assets
```

## License

MIT — see [LICENSE](LICENSE).
