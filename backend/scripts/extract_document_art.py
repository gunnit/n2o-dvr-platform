"""Extract the artwork of N2O's model DVR into committed, web-sized assets.

Usage: python extract_document_art.py <model.docx> <out_dir>

Reads ``word/media`` from the model DOCX and writes (see the layout-redesign
spec, Appendix A, for the key -> source mapping):

* ``cover_dvr.jpg``  - the single bitmap of ``image1.emf`` (EMR_STRETCHDIBITS)
* ``back_vera.jpg``  - ``image33.jpeg`` (aliased as ``cover_vera`` by the manifest)
* ``div_*.jpg``      - section divider pages (``div_generico`` is aliased to
                       ``div_ambienti`` by the manifest, so no extra file)
* ``sign_*.jpg``     - safety-sign panels, kept at native size
* ``vera_italia_mark.png`` - logo, alpha preserved

Page art is centre-cropped to A4 aspect (21/29.7) and resized to 1654 px wide
with Lanczos, never upscaled.
"""
from __future__ import annotations

import io
import struct
import sys
import zipfile
from pathlib import Path

from PIL import Image

A4_ASPECT = 21 / 29.7
PAGE_WIDTH = 1654

DIVIDERS = {
    "div_servizi_igienici": "image3.png",
    "div_macchine": "image4.png",
    "div_sostanze": "image5.png",
    "div_fattori_pericolo": "image6.png",
    "div_ambienti": "image7.jpeg",
    "div_mansioni": "image10.png",
    "div_dpi": "image12.png",
    "div_segnaletica": "image13.png",
    "div_formazione": "image19.png",
    "div_miglioramento": "image20.jpeg",
    "div_leggi": "image22.png",
    "div_sorveglianza": "image23.png",
    "div_riunione": "image24.png",
    "div_infortuni": "image25.png",
    "div_comportamenti": "image26.png",
    "div_gestione_dpi": "image27.png",
    "div_infrastrutture": "image28.png",
    "div_sensibili": "image29.png",
    "div_acquisti": "image30.png",
    "div_appalti": "image31.png",
    "div_dichiarazione": "image32.png",
}
SIGNS = {
    "sign_divieto": "image14.jpeg",
    "sign_avvertimento": "image15.jpeg",
    "sign_obbligo": "image16.jpeg",
    "sign_emergenza": "image17.jpeg",
    "sign_antincendio": "image18.jpeg",
}


def emf_single_bitmap(data: bytes) -> Image.Image:
    """Return the one EMR_STRETCHDIBITS bitmap embedded in an EMF."""
    off = 0
    found: list[Image.Image] = []
    while off + 8 <= len(data):
        rtype, size = struct.unpack_from("<II", data, off)
        if size < 8 or off + size > len(data):
            break
        if rtype == 81:  # EMR_STRETCHDIBITS
            fields = struct.unpack_from("<16x6i4I", data, off + 8)
            off_bmi, cb_bmi, off_bits, cb_bits = fields[6:10]
            bmi = data[off + off_bmi: off + off_bmi + cb_bmi]
            bits = data[off + off_bits: off + off_bits + cb_bits]
            header = b"BM" + struct.pack("<IHHI", 14 + len(bmi) + len(bits), 0, 0, 14 + len(bmi))
            im = Image.open(io.BytesIO(header + bmi + bits))
            im.load()
            found.append(im)
        off += size
    if len(found) != 1:
        raise SystemExit(f"expected exactly 1 STRETCHDIBITS in image1.emf, found {len(found)}")
    return found[0]


def to_rgb(im: Image.Image) -> Image.Image:
    """Flatten any alpha/palette image onto white."""
    if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
        im = im.convert("RGBA")
        bg = Image.new("RGB", im.size, (255, 255, 255))
        bg.paste(im, mask=im.getchannel("A"))
        return bg
    return im.convert("RGB")


def page_art(im: Image.Image) -> Image.Image:
    """Centre-crop to A4 aspect, then resize to PAGE_WIDTH (never upscale)."""
    im = to_rgb(im)
    w, h = im.size
    if w / h > A4_ASPECT:
        new_w = round(h * A4_ASPECT)
        left = (w - new_w) // 2
        im = im.crop((left, 0, left + new_w, h))
    else:
        new_h = round(w / A4_ASPECT)
        top = (h - new_h) // 2
        im = im.crop((0, top, w, top + new_h))
    if im.width > PAGE_WIDTH:
        im = im.resize((PAGE_WIDTH, round(PAGE_WIDTH / A4_ASPECT)), Image.LANCZOS)
    return im


def save_jpeg(im: Image.Image, path: Path, quality: int) -> None:
    im.save(path, "JPEG", quality=quality, progressive=True, optimize=True)


def main(docx: Path, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(docx) as z:
        def media(name: str) -> bytes:
            return z.read(f"word/media/{name}")

        def open_img(name: str) -> Image.Image:
            im = Image.open(io.BytesIO(media(name)))
            im.load()
            return im

        save_jpeg(page_art(emf_single_bitmap(media("image1.emf"))), out / "cover_dvr.jpg", 90)
        save_jpeg(page_art(open_img("image33.jpeg")), out / "back_vera.jpg", 80)
        for key, src in DIVIDERS.items():
            save_jpeg(page_art(open_img(src)), out / f"{key}.jpg", 80)
        for key, src in SIGNS.items():
            save_jpeg(to_rgb(open_img(src)), out / f"{key}.jpg", 85)
        (out / "vera_italia_mark.png").write_bytes(media("image21.png"))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    main(Path(sys.argv[1]), Path(sys.argv[2]))
