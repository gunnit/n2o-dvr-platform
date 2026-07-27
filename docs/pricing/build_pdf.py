"""Render a pricing deck HTML -> PDF.

Chrome (via Playwright) is the renderer: the deck is table-heavy and relies on
print backgrounds, so a browser engine beats reportlab here.

The NIUEXA logo is injected at build time rather than pasted into the HTML, and
it is cropped to its alpha bounding box first — the shipped PNG carries ~18 % of
transparent padding, which would otherwise offset the mark from the text column
it is supposed to align with.

Usage:
    python docs/pricing/build_pdf.py            # Italian (default)
    python docs/pricing/build_pdf.py en         # English
"""

from __future__ import annotations

import base64
import io
import pathlib
import sys

from PIL import Image
from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).parent

EDITIONS = {
    "it": ("pricing-deck-it.html", "Modello-di-Pricing-Piattaforma-DVR.pdf"),
    "en": ("pricing-deck.html", "N2O-DVR-Pricing-Strategy.pdf"),
}

BRAND_SKILL = pathlib.Path(
    r"C:\Users\Mato\AppData\Roaming\Claude\local-agent-mode-sessions\skills-plugin"
    r"\53ce0f4a-c99a-46de-a11e-fa2aca44a208\79c9d91b-1e12-456c-a096-5de6e0fb6141"
    r"\skills\niuexa-brand"
)

FOOTERS = {
    "it": ("Piattaforma DVR &middot; Modello di pricing &middot; Riservato", "NIUEXA"),
    "en": ("N2O DVR Platform &middot; Pricing Strategy &middot; Confidential", "NIUEXA"),
}

EMPTY_HEADER = '<div style="display:none"></div>'


def footer_template(edition: str) -> str:
    left, right = FOOTERS[edition]
    return f"""
<div style="width:100%;font-family:Inter,Segoe UI,Arial,sans-serif;font-size:7pt;
            color:#94a3b8;padding:0 16mm;display:flex;justify-content:space-between;
            border-top:1px solid #e2e8f0;padding-top:2mm;margin-top:3mm">
  <span style="color:#64748b">{left}</span>
  <span>{right} &nbsp;|&nbsp; <span class="pageNumber"></span> / <span class="totalPages"></span></span>
</div>
"""


def tight_logo_b64() -> str:
    """Return the logo cropped to its visible pixels, as base64 PNG."""
    im = Image.open(BRAND_SKILL / "assets" / "logo.png").convert("RGBA")
    im = im.crop(im.split()[3].getbbox())
    # 1024px source is far more than a 22mm print mark needs; halve it to keep
    # the PDF small without touching the rendered quality at 300+ dpi.
    im.thumbnail((512, 512), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def main() -> int:
    edition = (sys.argv[1] if len(sys.argv) > 1 else "it").lower()
    if edition not in EDITIONS:
        print(f"unknown edition {edition!r}; use one of {list(EDITIONS)}")
        return 2

    src_name, out_name = EDITIONS[edition]
    src, out = HERE / src_name, HERE / out_name

    html = src.read_text(encoding="utf-8").replace("__LOGO_B64__", tight_logo_b64())
    tmp = HERE / f"_build-{edition}.html"
    tmp.write_text(html, encoding="utf-8")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(tmp.resolve().as_uri(), wait_until="networkidle")
        # Promote each table's header row into a real <thead> so Chrome repeats
        # it when a long table splits across pages. Done in the DOM rather than
        # by rewriting the source, which keeps the HTML readable.
        page.evaluate(
            """() => {
              for (const t of document.querySelectorAll('table')) {
                if (t.tHead) continue;
                const first = t.rows[0];
                if (!first || !first.cells.length) continue;
                if ([...first.cells].some(c => c.tagName !== 'TH')) continue;
                t.createTHead().appendChild(first);
              }
            }"""
        )
        # Give webfonts a beat to settle before layout is frozen into the PDF.
        page.wait_for_timeout(1200)
        page.pdf(
            path=str(out),
            format="A4",
            print_background=True,
            display_header_footer=True,
            header_template=EMPTY_HEADER,
            footer_template=footer_template(edition),
            # Top margin is 0 so the cover bleeds to the sheet edge; content
            # pages re-create it as .page padding.
            margin={"top": "0mm", "bottom": "16mm", "left": "0mm", "right": "0mm"},
        )
        browser.close()

    tmp.unlink(missing_ok=True)
    print(f"wrote {out}  ({out.stat().st_size / 1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
