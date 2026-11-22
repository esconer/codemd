# Research: Which repository content should stay text, and which can become images?

*Generated 2026-11-21 · Sources: 15 · Confidence: Medium–High for direction, Low for exact numbers in your setup*

## Executive summary

Rendering text as images is a real, measurable token compression technique, but it is **lossy and task-dependent**. The right policy is not “all repo → images” or “all repo → text”; it is a **criticality router**:

- **Text** for anything the model must *copy exactly*: identifiers, signatures, config keys, constants, error strings, diffs, file paths, instructions, factsheets.
- **Images** for high-volume, *gist-tolerant*, read-only context: large prose docs, licenses/changelogs, logs, old conversation/tool output, unchanged files, bulk implementation bodies the model should understand but not edit.
- **Sidecars** for metadata (exclusion reports, stats) — never in the paid context.

Evidence:

- Visual text can cut decoder tokens roughly in half with little accuracy loss on retrieval/summarization ([Text or Pixels? It Takes Half](https://arxiv.org/html/2510.18279v2)).
- Code-specific studies find images viable at up to 4–8× compression for **summarization, clone detection, QA**, but **code completion / exact editing** degrades earlier, typically beyond 2–4× for most models ([CodeOCR](https://arxiv.org/html/2602.01785v2)).
- An independent test with planted IDs/numbers found text→images saved 64–81% of tokens, but exact identifiers that were *not* in an accompanying text “factsheet” were recalled **0/80 times**, and numbers were frequently misread or silently fabricated ([DEV Community experiment](https://dev.to/jaehyun_cho_0dff271e0d2e5/sending-text-as-images-cut-my-claude-tokens-by-up-to-81-it-also-started-inventing-numbers-57ol)).
- Provider accounting differs sharply. A 675-pair study found large aggregate reductions (Anthropic 86.5%, OpenAI 80.6%, Gemini 75.8%) **but Gemini images cost 6.95× more than text at 20 lines** and only cross below text around 200 lines ([Pixels for Programs?](https://arxiv.org/html/2607.21672v1)). Page boundaries can even cause non-monotonic token counts.

Practical conclusion for your AI Studio review loop: **keep diffs, patches, signatures, configs and facts as text; rasterize only bulky read-only context; batch enough text per image to amortize fixed vision cost; and always keep the text parts on disk as ground truth.**

## 1. What “important” actually means for routing

Use this decision rule:

1. **Will the model need to copy it exactly?** (patch context line, function name, constant, hash, SQL, key, path, number) → **text**.
2. **Will it only need the gist?** (summarize architecture, classify, decide where to look, understand overall control flow) → **image candidate**.
3. **Is it small?** (<~200 lines / <~8k chars, especially on Gemini) → **text**; image overhead dominates.
4. **Is it high-volume, read-only, and gist-tolerant?** (long prose, logs, unchanged files, licenses, old history, generated/vendored code) → **image**.
5. **Unsure?** → **text**.

This follows directly from the evidence that exact strings degrade first: CodeOCR reports token-level errors at 1–2× compression, line-level at 2–4×, block-level at 4–8× ([CodeOCR RQ5](https://arxiv.org/html/2602.01785v2)). The DEV experiment’s “0/80 for IDs not in the factsheet” is the same phenomenon in practice.

## 2. What studies say about quality by task

| Task | Image tolerance | Source |
| --- | --- | --- |
| Code summarization | High; several models maintain/improve at 4–8× | [CodeOCR](https://arxiv.org/html/2602.01785v2) |
| Clone detection / “are these equivalent?” | Very high; moderate compression sometimes *helps* | [CodeOCR](https://arxiv.org/html/2602.01785v2) |
| Code QA / architecture questions | Moderate; Gemini-3 resilient to 8×, most models degrade beyond 2–4× | [CodeOCR](https://arxiv.org/html/2602.01785v2) |
| Code completion / exact patching | Lowest; keep edit targets in text | [CodeOCR](https://arxiv.org/html/2602.01785v2), [DEV experiment](https://dev.to/jaehyun_cho_0dff271e0d2e5/sending-text-as-images-cut-my-claude-tokens-by-up-to-81-it-also-started-inventing-numbers-57ol) |
| Long-context retrieval (needle) | ~2× compression near-lossless for GPT-4.1-mini / Qwen2.5-VL-72B | [Text or Pixels? It Takes Half](https://arxiv.org/html/2510.18279v2) |
| Document summarization | Text-as-image beat LLMLingua-2 / Select-Context at matched compression | [Text or Pixels?](https://arxiv.org/html/2510.18279v2), [EMNLP 2025 version](https://aclanthology.org/2025.findings-emnlp.558.pdf) |

Model strength matters: Gemini-3 family and GPT-5 class models handle code images far better than older/weaker VLMs; Qwen-3-VL and GLM-4.6v degraded on several code tasks ([CodeOCR](https://arxiv.org/html/2602.01785v2)). So your results in AI Studio depend on which Gemini version you pick.

## 3. The “factsheet” pattern — the most directly useful design

The pxpipe experiment used **images for bulk text + a text factsheet of exact identifiers**. Result: planted IDs present in the factsheet were recalled (Opus 58/60); IDs absent from it were recalled **0/80**. Numbers were the weak spot (best model 44/60). Wrong values looked plausible (94392 → 9392) ([source](https://dev.to/jaehyun_cho_0dff271e0d2e5/sending-text-as-images-cut-my-claude-tokens-by-up-to-81-it-also-started-inventing-numbers-57ol), [pxpipe writeup](https://gattyworks.com/news/pxpipe-cut-llm-token-costs)).

Apply this to code review:

- Generate `FACTS.md` (text): file paths, public type/function signatures, constants, enum variants, config keys, error strings, changed lines, and any identifier the model may reference in a patch.
- Generate `CONTEXT.*.png` (images): the full bodies of large files, prose docs, old history, logs, licenses.
- Prompt: “Use FACTS.md for exact names; images are for understanding only. Quote nothing from images verbatim.”

This converts an unsafe lossy channel into a safe hybrid: the model reasons over compressed context but copies from exact text.

## 4. Provider economics — critical for Google AI Studio

Google’s docs: images ≤384×384 = 258 tokens; larger images are tiled (Gemini 2.x) at 258 tokens/tile. Gemini 3/4 use fixed `media_resolution` budgets: `low` 280, `medium` 560, `high`/default **1120**, `ultra_high` 2240 tokens per image ([token docs](https://aistudio.google.com/docs/tokens), [media resolution](https://ai.google.dev/gemini-api/docs/media-resolution)). AI Studio’s chat UI may not expose this knob, so **measure actual usage metadata**.

The cross-provider study found:
- Anthropic / OpenAI: images cheaper than text at every tested size.
- Gemini: images **6.95× more expensive** at 20 lines; ratio ~1.46 at 100 lines; crosses parity at 200 lines; reaches ~0.13 at 1600 lines.
- Image token counts can be non-monotonic across page boundaries.

Implication: **do not image small snippets or single files**. Batch read-only material into large pages (our 1800×4096 @ font 20 holds ~15–18k usable chars). For Gemini, prefer fewer, denser images over many small ones.

## 5. Rendering choices that matter

- **Resolution/legibility:** MLLM OCR matches conventional OCR around ~300 ppi and degrades strongly below ~150 ppi ([arXiv:2503.23667](https://arxiv.org/html/2503.23667v1)). Our 20 px monospace at 1800×4096 is reasonably legible; shrinking font to gain density has a cliff.
- **Syntax highlighting:** CodeOCR found plain black-on-white baseline, with bold/highlight giving 1–3% gains at 1–2× compression, but diminishing/negative at 8× ([source](https://arxiv.org/html/2602.01785v2)). If added, keep it subtle.
- **Layout:** preserve line breaks and indentation; our fence-continuation splitting is aligned with this.
- **Order:** text instructions should be adjacent to / before the image; image-first helps some math tasks, text-first helps grammar/instruction tasks ([arXiv:2410.03062](https://arxiv.org/html/2410.03062)). For coding, text instruction + factsheet first is safest.
- **Compression target:** stay ≤2× for anything you may edit; 4× is okay for gist/summary; 8× only for robust models and gist-only tasks.

## 6. Proposed implementation for `codemd`

Add an opt-in `--hybrid` mode (default untouched):

| Output | Modality | Contents |
| --- | --- | --- |
| `FACTS.md` | text | manifest, signatures, constants, config keys, changed hunks/diff, file paths, exclusion report |
| `BULK.part*.png` | image | full bodies of large read-only files, prose docs, licenses, logs, generated assets |
| `Content.part*.md` | text (optional) | full text ground truth, not necessarily sent |

Routing rules (initial heuristic):

1. `--diff` / `--changed` output → **always text** (patch exactness).
2. Manifest / exclusion report → **always text** sidecar.
3. Per-file: if file is small (`<8k chars`) or in a “critical exactness” extension set (`.toml`, `.json`, `.yml`, `.properties`, `.lock`, `.proto`, `.sql`, `.gradle`, CMake, `.gitignore`) → text.
4. Source files (`.rs`, `.kt`, `.java`, `.py`, …): emit **signature skeleton as text**, full body as image; if file `<8k chars`, whole file as text.
5. Docs (`*.md` prose), changelogs, licenses, logs → image if large, text if small.
6. Binary/skip as today.

Later refinement: use a small local model or tree-sitter to extract the factsheet more accurately than regex. Do **not** put the text factsheet inside the image — that defeats the purpose.

## 7. Concrete workflows for your review loop

**Round 1 — initial full review**

```bash
# Text: manifest + facts + diff + critical files
./codemd -C /path/to/repo --manifest -o REPOMAP.md
./codemd -C /path/to/repo --diff --report Content.report.md
# Images: bulk read-only context (future --hybrid)
./codemd -C /path/to/repo --hybrid --report Content.report.md
```

Prompt: “Review architecture and correctness. Use FACTS.md / REPOMAP.md for exact names; images give you the full bodies. Return unified diffs.”

**Round 2 — after applying patches locally**

```bash
./codemd -C /path/to/repo --diff --report Content.report.md
```

Usually **no images** for round 2: the diff is small and exactness dominates.

## 8. How to validate in your own setup (cheap A/B)

1. Pick 3 large files + 1 architecture doc.
2. Send variant A: text only. Variant B: factsheet text + image bodies. Variant C: images only.
3. Ask the same 10 questions: 5 “exact” (function names, constants, error strings), 5 “gist” (what does this module do, where is X handled).
4. Record exact-match accuracy and provider `usage` token counts.
5. Keep images only if gist accuracy is within ~3 points of text and exact accuracy on factsheet items stays ~100%.

This mirrors the published methodology and will tell you whether your chosen Gemini version behaves like the robust Gemini-3 family or the weaker models.

## Gaps / uncertainty

- No study I found tests this exact workflow (AI Studio expert review → patches → re-upload) on this repo.
- Most code-image evidence uses 2240×2240 renderings and API models, not our 1800×4096 Pillow renderer; absolute numbers will differ.
- AI Studio may not expose `media_resolution`; Gemini accounting may change. Version your measurements.
- Vendor claims (pxpipe 59–70% bill cut, Moxby 97% context-token cut) are directionally consistent but are self-reported, not independent peer review ([pxpipe](https://gattyworks.com/news/pxpipe-cut-llm-token-costs), [Moxby](https://moxby.com/introducing-the-multi-layered-token-condensor)).
- I did not run the A/B experiment in section 8; it is a proposed next step.

## Sources

1. [CodeOCR: On the Effectiveness of VLMs in Code Understanding](https://arxiv.org/html/2602.01785v2) — ISSTA ’26; 7 models, 4 code tasks, 1–8× visual compression.
2. [Pixels for Programs? Cross-Provider Input-Token Accounting for Code as Text and Images](https://arxiv.org/html/2607.21672v1) — 675 paired requests; provider break-even and page-boundary anomalies.
3. [Text or Pixels? It Takes Half](https://arxiv.org/html/2510.18279v2) — ~2× compression on RULER/CNN-DailyMail with minor accuracy loss.
4. [Text or Pixels? (EMNLP 2025 Findings)](https://aclanthology.org/2025.findings-emnlp.558.pdf) — peer-reviewed version of the above.
5. [DEV Community: tokens cut 81%, then invented numbers](https://dev.to/jaehyun_cho_0dff271e0d2e5/sending-text-as-images-cut-my-claude-tokens-by-up-to-81-it-also-started-inventing-numbers-57ol) — exact-ID factsheet experiment.
6. [pxpipe writeup](https://gattyworks.com/news/pxpipe-cut-llm-token-costs) — proxy that images bulky context; self-reported 59–70% savings.
7. [Google AI Studio token docs](https://aistudio.google.com/docs/tokens) — image token accounting.
8. [Gemini media resolution docs](https://ai.google.dev/gemini-api/docs/media-resolution) — fixed per-image budgets for Gemini 3/4.
9. [Gemini image understanding limits](https://ai.google.dev/gemini-api/docs/image-understanding) — 3,600 images/request, tiling rules.
10. [Context-Independent OCR with MLLMs: resolution effects](https://arxiv.org/html/2503.23667v1) — ~300 ppi threshold, <150 ppi degradation.
11. [OCRBench v2](https://arxiv.org/html/2501.00321v2) — VLM OCR strengths and failure modes.
12. [CodeShrink: Adaptive Visual Compression for Code](https://arxiv.org/html/2607.29637) — adaptive resolution / sparse blank regions.
13. [LensVLM: selective context expansion](https://arxiv.org/html/2605.07019v2) — compressed scan + expand relevant images on demand.
14. [VIST: Vision-centric Token Compression (NeurIPS 2025)](https://proceedings.neurips.cc/paper_files/paper/2025/file/2f8b56543953d60f262fb2c4b85c50b3-Paper-Conference.pdf) — slow path for exact tokens, fast path for distant gist.
15. [Image First or Text First?](https://arxiv.org/html/2410.03062) — modality sequencing effects.

## Methodology

Ran 8 web searches covering code-image quality, token accounting, rendering best practices, hybrid prompting, and visual context compression; fetched 4 key sources in full (CodeOCR, Pixels for Programs, Text or Pixels, DEV experiment). Prioritized 2025–2026 papers, official Google docs, and independent experiments. Vendor claims are labelled as such. No local A/B experiment was run for this report.
