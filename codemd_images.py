#!/usr/bin/env python3
"""Render text files into LLM-readable PNG images.

Designed for codemd's split Markdown parts: each part becomes one or more
pages, with generous resolution and a monospace font so code stays legible.
"""

import argparse
import os
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    sys.exit("codemd_images: Pillow is required (pip install pillow)")


DEFAULT_FONTS = [
    "/usr/share/fonts/dejavu-sans-mono-fonts/DejaVuSansMono.ttf",
    "/usr/share/fonts/liberation-mono-fonts/LiberationMono-Regular.ttf",
    "/usr/share/fonts/google-noto/NotoSansMono-Regular.ttf",
]


def pick_font(path):
    if path:
        if not os.path.isfile(path):
            sys.exit(f"codemd_images: font file not found: {path}")
        return path
    for candidate in DEFAULT_FONTS:
        if os.path.isfile(candidate):
            return candidate
    sys.exit("codemd_images: no monospace font found; pass --font PATH")


def wrap_line(text, draw, font, max_width):
    """Greedy character wrap that preserves leading indentation."""
    if draw.textlength(text, font=font) <= max_width:
        return [text]

    stripped = text.lstrip()
    indent = text[: len(text) - len(stripped)]
    result = []
    current = ""
    for char in text:
        trial = current + char
        if draw.textlength(trial, font=font) <= max_width:
            current = trial
        else:
            result.append(current)
            current = indent + char
    if current:
        result.append(current)
    return result or [""]


def render_file(path, args, font_path):
    raw = Path(path).read_text(encoding="utf-8", errors="replace")
    lines = raw.splitlines() or [""]

    font = ImageFont.truetype(font_path, args.font_size)
    small = ImageFont.truetype(font_path, max(10, args.font_size - 4))

    # Measure with a throwaway image.
    probe = Image.new("RGB", (args.width, args.height))
    probe_draw = ImageDraw.Draw(probe)
    char_width = max(1.0, probe_draw.textlength("M", font=font))
    max_chars = max(1, int((args.width - 2 * args.margin) // char_width))

    visual_lines = []
    for line in lines:
        visual_lines.extend(wrap_line(line, probe_draw, font, args.width - 2 * args.margin))

    line_height = args.font_size + args.line_gap
    header_height = args.font_size + args.line_gap * 2
    content_height = args.height - header_height - 2 * args.margin
    per_page = max(1, content_height // line_height)
    total_pages = max(1, (len(visual_lines) + per_page - 1) // per_page)

    if args.theme == "dark":
        background, foreground, meta, rule = "#0d1117", "#d6deeb", "#8b949e", "#30363d"
    else:
        background, foreground, meta, rule = "#ffffff", "#1a1a1a", "#6b7280", "#d1d5db"

    base = Path(path).stem
    outdir = args.outdir or str(Path(path).parent)
    os.makedirs(outdir, exist_ok=True)

    written = []
    for page in range(total_pages):
        image = Image.new("RGB", (args.width, args.height), background)
        draw = ImageDraw.Draw(image)
        label = f"{Path(path).name}  |  page {page + 1}/{total_pages}  |  ~{max_chars} chars/line"
        draw.text((args.margin, args.margin // 2), label, font=small, fill=meta)
        draw.line(
            [(args.margin, header_height), (args.width - args.margin, header_height)],
            fill=rule,
            width=1,
        )

        chunk = visual_lines[page * per_page : (page + 1) * per_page]
        y = header_height + args.line_gap
        for line in chunk:
            draw.text((args.margin, y), line, font=font, fill=foreground)
            y += line_height

        if total_pages == 1:
            name = f"{base}.png"
        else:
            name = f"{base}.p{page + 1:02d}.png"
        out_path = os.path.join(outdir, name)
        image.save(out_path, "PNG", optimize=True)
        written.append(out_path)

    print(f"codemd_images: {path} -> {len(written)} image(s)")
    for out_path in written:
        print(f"  {out_path}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="+", help="text files to render")
    parser.add_argument("--width", type=int, default=1800, help="image width in pixels")
    parser.add_argument("--height", type=int, default=4096, help="image height in pixels")
    parser.add_argument("--font-size", type=int, default=20, help="monospace font size")
    parser.add_argument("--line-gap", type=int, default=6, help="extra pixels between lines")
    parser.add_argument("--margin", type=int, default=40, help="side/top margin")
    parser.add_argument("--font", help="path to a monospace TTF font")
    parser.add_argument("--theme", choices=("light", "dark"), default="light")
    parser.add_argument("--outdir", help="output directory (default: same as each input)")
    args = parser.parse_args()

    if args.width < 400 or args.height < 400:
        sys.exit("codemd_images: --width/--height must be at least 400")
    if args.font_size < 8:
        sys.exit("codemd_images: --font-size must be at least 8")

    font_path = pick_font(args.font)
    for file in args.files:
        render_file(file, args, font_path)


if __name__ == "__main__":
    main()
