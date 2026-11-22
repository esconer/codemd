# codemd

A CLI that exports a Git repository into a single Markdown file (or split parts /
images), while respecting `.gitignore` plus a configurable extra-ignore list.
It also reports every excluded path, character totals, and an estimated token
count.

This project was moved out of `audioshare-ultra` so it can be reused on any repo.

## Files

- `codemd` — the CLI (Bash)
- `codemd_images.py` — optional PNG renderer for `--to-images` (requires Pillow)

## Quick start

```bash
# Export the repository that contains this script (default root = script dir)
./codemd

# Target any other repo
./codemd -C /path/to/repo

# Export to a specific file
./codemd -C /path/to/repo -o /tmp/export.md
```

By default the output is `Content.md` in the repository root, with a header
containing file count, character count, estimated tokens, and an
`Excluded files` table at the end. The default behaviour is a full-repo export.

## Options

```
-C, --root DIR          Repository root (default: directory of this script)
-o, --output FILE       Output Markdown file (default: Content.md)
-e, --exclude PATTERN   Extra ignore pattern (repeatable)
    --exclude-from FILE Read extra ignore patterns from FILE
    --include-ignored   Also export files ignored by .gitignore
    --expand-ignored    List every ignored file (no collapsing)
    --max-list N        Collapse ignored dirs with more than N files
    --collapse PATTERN  Collapse a directory name matching PATTERN to one line
    --no-excluded       Omit the "Excluded files" table from the output
    --no-header         Omit the top-level header
-q, --quiet             Do not print individual included/excluded paths
```

### Selection / LLM helpers (opt-in)

```
    --manifest          Write a file manifest (no code)
    --files PATH        Export only PATH (repeatable; exact files bypass .gitignore)
    --glob PATTERN      Export only files matching PATTERN (repeatable)
    --changed [A [B]]   Export only files changed vs A, or between A and B
    --diff [A [B]]      Export only a unified diff vs A, A..B, or A B
    --with-diff [A [B]] Add a unified diff vs A, A..B, or A B to a full export
    --commits [RANGE]   Write commits as Markdown with messages and diffs
    --pr [BASE]         Like --commits with BASE..HEAD (default base: main)
    --budget N          Skip files that would exceed ~N estimated tokens
    --profile llm       Skip lockfiles, licenses, wrappers, generated assets
    --report FILE       Write exclusion report to FILE (omitted from payload)
    --split-chars N     Split output into ~N-character parts (part1, part2, ...)
    --to-images         Render parts to PNG images (experimental; needs Pillow)
    --image-width PX    Image width (default 1800)
    --image-height PX   Image height (default 4096)
    --image-font-size N Monospace font size (default 20)
    --image-theme light|dark
    --image-outdir DIR  Where to write images
```

Run `./codemd --help` for the full list and examples.

### Split naming

With `--split-chars N`:

- Files that fit within the budget are **never split** across parts.
- Only a file larger than the budget is split; those parts are named
  `Content.part7-src__lib.rs-1of3.md`, `Content.part8-src__lib.rs-2of3.md`, etc.
- Ordinary parts keep `Content.part1.md`.
- `Content.parts.md` is written alongside the parts and maps every part to the
  files (and file pieces) it contains.
- If one source line is longer than the budget (minified code, long JSON), it
  is wrapped at character boundaries so no part exceeds the limit.

## Workflow examples

Initial full review:

```bash
./codemd -C /path/to/repo --profile llm --report /path/to/repo/Content.report.md
```

After applying patches locally (send only what changed):

```bash
./codemd -C /path/to/repo --diff --report /path/to/repo/Content.report.md
```

Diff between two commits (or a range):

```bash
./codemd -C /path/to/repo --diff abc123 def456 -o DIFF.md
./codemd -C /path/to/repo --diff HEAD~5..HEAD -o DIFF.md
```

Commit history / PR as Markdown:

```bash
./codemd -C /path/to/repo --commits HEAD~5..HEAD -o HISTORY.md
./codemd -C /path/to/repo --pr main -o PR.md
```

Repo map only (~1–2k tokens):

```bash
./codemd -C /path/to/repo --manifest -o /tmp/REPOMAP.md
```

100k-character parts:

```bash
./codemd -C /path/to/repo --split-chars 100000 --report Content.report.md
```

Text chunks as images:

```bash
./codemd -C /path/to/repo --split-chars 20000 --to-images --report Content.report.md
```

## Notes

- Token estimates use the English-prose heuristic of ~4 characters/token; code
  usually tokenizes more densely.
- Generated `Content*.md` parts and images are automatically excluded on later
  runs so they don't get re-exported.
- Images are experimental: keep the `.part*.md` files as ground truth and
  spot-check readability before sending to a vision model.
