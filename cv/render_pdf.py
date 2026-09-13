#!/usr/bin/env python3
"""Render a tailored CV HTML to a single-page A4 PDF and verify the rendering.

WHY THIS EXISTS
---------------
The CV template's print CSS sets the container width to `210mm / 0.81` (~259mm)
and relies on `zoom: 0.81` to shrink it back to A4 width. Chrome honors `zoom`,
so its "Download as PDF" button looks correct. WeasyPrint (used here, since the
sandbox cannot run a real browser) does NOT support `zoom`, so rendered as-is the
container stays ~259mm wide and the right edge gets CLIPPED.

This script overrides that hack: it forces a true 210mm container, supplies the
exact Tailwind utility classes the template uses as static CSS (the Tailwind CDN
is network-blocked in the sandbox), bakes in proper page margins, and auto-scales
the content down until it fits on exactly one A4 page.

USAGE
-----
    python3 cv/render_pdf.py cv/tailored/<id>.html            # -> same path .pdf + .preview.png
    python3 cv/render_pdf.py <in.html> -o <out.pdf> --preview <out.png>

It prints the chosen scale and page count. ALWAYS open the .preview.png and
visually confirm: (1) nothing is cut off the right edge, (2) it is one page,
(3) the bottom section is not crammed against the page edge.
"""
import re, os, sys, argparse
import weasyprint, fitz  # fitz = PyMuPDF

# Static definitions of the exact Tailwind utility classes used by base_cv.html.
# If a future template adds new classes, add them here or they will render unstyled.
TAILWIND_UTILS = r"""
*{box-sizing:border-box;}
body{margin:0;font-family:Arial,"Liberation Sans",Helvetica,sans-serif;color:#111827;}
h1,h2,h3,p{margin:0;}
.flex{display:flex;}.items-start{align-items:flex-start;}
.gap-2{gap:.5rem;}.gap-6{gap:1.5rem;}
.w-1\/3{width:33.3333%;}.w-2\/3{width:66.6667%;}
.flex-shrink-0{flex-shrink:0;}.max-w-5xl{max-width:64rem;}
.mx-auto{margin-left:auto;margin-right:auto;}.min-h-screen{min-height:100vh;}
.p-8{padding:2rem;}.px-6{padding-left:1.5rem;padding-right:1.5rem;}.py-2{padding-top:.5rem;padding-bottom:.5rem;}
.pb-1{padding-bottom:.25rem;}.pb-4{padding-bottom:1rem;}
.mb-1{margin-bottom:.25rem;}.mb-2{margin-bottom:.5rem;}.mb-3{margin-bottom:.75rem;}.mb-4{margin-bottom:1rem;}.mb-6{margin-bottom:1.5rem;}
.mt-0\.5{margin-top:.125rem;}.mt-1{margin-top:.25rem;}
.space-y-1>*+*{margin-top:.25rem;}.space-y-2>*+*{margin-top:.5rem;}.space-y-3>*+*{margin-top:.75rem;}.space-y-4>*+*{margin-top:1rem;}
.text-sm{font-size:.875rem;line-height:1.25rem;}.text-base{font-size:1rem;line-height:1.5rem;}.text-lg{font-size:1.125rem;line-height:1.75rem;}.text-4xl{font-size:2.25rem;line-height:2.5rem;}
.font-medium{font-weight:500;}.font-semibold{font-weight:600;}.font-bold{font-weight:700;}
.uppercase{text-transform:uppercase;}.tracking-wide{letter-spacing:.025em;}.leading-relaxed{line-height:1.625;}.break-all{word-break:break-word;}
.bg-gray-100{background:#fff;}.bg-white{background:#fff;}.bg-blue-900{background:#1e3a8a;}
.text-white{color:#fff;}.text-gray-900{color:#111827;}.text-gray-700{color:#374151;}.text-gray-600{color:#4b5563;}.text-blue-900{color:#1e3a8a;}.text-blue-700{color:#1d4ed8;}
.border-b-2{border-bottom:2px solid;}.border-b-4{border-bottom:4px solid;}.border-blue-900{border-color:#1e3a8a;}
.rounded{border-radius:.25rem;}.shadow-lg{box-shadow:none;}
svg{display:inline-block;vertical-align:top;}
"""

# Page margins baked into the container (top right bottom left). Bottom is generous
# so the last section never crams against the page edge.
PAGE_PADDING = "12mm 14mm 16mm 14mm"


def build_html(src: str, scale: float) -> str:
    html = open(src, encoding="utf-8").read()
    # Drop the runtime Tailwind CDN script (network-blocked; replaced by static CSS).
    html = re.sub(r'<script src="https://cdn\.tailwindcss\.com"></script>\s*', '', html)
    override = f"""
<style id="render-pdf-fix">
html{{font-size:{16*scale:.3f}px;}}
{TAILWIND_UTILS}
@media print {{
  .print-container{{width:210mm!important;min-height:0!important;zoom:normal!important;
    padding:{PAGE_PADDING}!important;box-shadow:none!important;}}
  body>div{{padding:0!important;margin:0!important;background:#fff!important;}}
  body>div>div{{max-width:none!important;margin:0!important;padding:0!important;}}
}}
</style>
"""
    return html.replace("</head>", override + "\n</head>")


def render(src: str, out: str, scale: float) -> int:
    weasyprint.HTML(string=build_html(src, scale),
                    base_url=os.path.dirname(os.path.abspath(src))).write_pdf(out)
    with fitz.open(out) as doc:
        return doc.page_count


def autofit(src: str, out: str, hi: float = 0.95, lo: float = 0.55, step: float = 0.02):
    """Largest scale that still fits on one A4 page."""
    s = hi
    while s >= lo - 1e-9:
        if render(src, out, round(s, 3)) == 1:
            return round(s, 3)
        s -= step
    return None


def save_preview(pdf: str, png: str, dpi: int = 150):
    with fitz.open(pdf) as doc:
        doc[0].get_pixmap(dpi=dpi).save(png)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("-o", "--output")
    ap.add_argument("--preview")
    ap.add_argument("--scale", type=float, help="force a fixed scale instead of auto-fit")
    args = ap.parse_args()

    out = args.output or os.path.splitext(args.input)[0] + ".pdf"
    preview = args.preview or os.path.splitext(out)[0] + ".preview.png"

    if args.scale:
        pages = render(args.input, out, args.scale)
        scale = args.scale
    else:
        scale = autofit(args.input, out)
        if scale is None:
            print("ERROR: could not fit on one page even at minimum scale; trim content.")
            sys.exit(1)
        pages = 1

    save_preview(out, preview)
    print(f"OK  scale={scale}  pages={pages}")
    print(f"PDF: {out}")
    print(f"Preview PNG (INSPECT THIS): {preview}")


if __name__ == "__main__":
    main()
