"""Rebuild the landing hero's derived images from the approved render.

The hero (src/components/landing/hero-stage.tsx) shows the "modello in scala"
workshop with live risk pins and a WebGL depth effect. Both of its images are
derived from one approved render, so a new render means re-running this:

  src/components/landing/assets/officina-modello.webp
      the render with its five baked-in pins inpainted away (LaMa, inside the
      pin masks only — every other pixel is the render's own), cropped to the
      model and padded on the right with the backdrop's own navy;
  src/components/landing/assets/officina-profondita.webp
      its relative depth (Depth Anything V2 Large; 1 = near), 1024×512 so
      WebGL1 can mipmap it, with near edges dilated ~2px so a moving object
      carries its outline instead of leaving a sliver behind.

It then prints what hero-scene.ts hard-codes and must be updated by hand
when the render changes: the stage size, the scan range, the ground-plane fit
and the scan threshold of each live pin (LIVE_PINS below mirrors HERO_PINS).
Constants are always read back from the written depth map, i.e. from what the
shader samples. The shader smooths the scan coordinate with a mip bias rather
than this script's blur, so live thresholds can run ~0.03 (≈30ms) later; only
the pins' timing depends on them.

Not part of the build; needs Python 3.11+ and
  pip install --index-url https://download.pytorch.org/whl/cpu torch
  pip install transformers pillow opencv-python-headless numpy simple-lama-inpainting
(uninstall any CUDA torchvision simple-lama pulls in: transformers then fails
to import). The current source render is in git history:
  git show 5411970:frontend/public/landing/modello-officina.webp > render.webp
  python scripts/build-hero-depth.py render.webp src/components/landing/assets

To move a live pin, edit LIVE_PINS and hero-scene.ts together, then reprint
the constants without rebuilding anything (no ML dependencies needed):
  python scripts/build-hero-depth.py --constants src/components/landing/assets
"""

import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

# The five pins baked into the 2400×1357 source render, all inpainted away:
# head centre, head radius, stick x, and the y where the stick enters the
# machine. Measured on the render.
BAKED_PINS = {
    "fresatrice": ((1464.7, 253.5), 16, 1466, 312),
    "trapano": ((1626.0, 291.0), 15, 1626, 334),
    "tornio": ((1104.8, 424.1), 15, 1108, 491),
    "tornio-2": ((1144.1, 606.9), 15, 1146, 667),
    "saldatura": ((1879.2, 507.6), 16, 1879, 617),
}
# The live pins' bases in stage space, as in HERO_PINS (hero-scene.ts).
LIVE_PINS = {
    "pavimento": (0.3178, 0.4032),
    "fresatrice": (0.4033, 0.2159),
    "trapano": (0.4922, 0.2333),
    "saldatura": (0.6328, 0.4579),
}
# Crop around the model (it spans x 800..2364, y 104..1230), then pad the
# right edge: the render leaves only 36px of navy past the plinth's corner.
CROP = (740, 40, 2400, 1300)
PAD_RIGHT = 140
# Scan coordinate s = a·u + b·v + c·depth, fitted so that s is constant along
# world verticals and along the right wall on the floor (see hero-scene.ts).
SCAN_AXIS = (2.403, -0.68, -1.0)
DEPTH_SIZE = (1024, 512)


def inpaint_pins(img: np.ndarray) -> np.ndarray:
    h, w = img.shape[:2]
    mask = np.zeros((h, w), np.uint8)
    for (cx, cy), r, sx, by in BAKED_PINS.values():
        cv2.circle(mask, (round(cx), round(cy)), r + 5, 255, -1, lineType=cv2.LINE_AA)
        cv2.rectangle(mask, (sx - 4, round(cy)), (sx + 4, by + 2), 255, -1)
        cv2.ellipse(mask, (sx, by), (7, 4), 0, 0, 360, 255, -1)
    mask = cv2.dilate(mask, np.ones((3, 3), np.uint8))
    from simple_lama_inpainting import SimpleLama

    rgb = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    out = SimpleLama()(rgb, Image.fromarray(mask))
    out = cv2.cvtColor(np.array(out), cv2.COLOR_RGB2BGR)[:h, :w]
    alpha = cv2.GaussianBlur(mask, (0, 0), 1.2).astype(np.float32)[..., None] / 255
    alpha = np.clip(alpha * 1.4, 0, 1)
    return (out * alpha + img * (1 - alpha)).round().astype(np.uint8)


def crop_and_pad(img: np.ndarray) -> np.ndarray:
    x0, y0, x1, y1 = CROP
    crop = img[y0:y1, x0:x1].astype(np.float32)
    edge = crop[:, -24:].mean(axis=1, keepdims=True)
    out = np.concatenate([crop, np.repeat(edge, PAD_RIGHT, axis=1)], axis=1)
    seam = x1 - x0
    out[:, seam - 40 : seam + 60] = cv2.GaussianBlur(
        out[:, seam - 40 : seam + 60], (0, 0), sigmaX=10, sigmaY=0.1
    )
    out[:, : seam - 40] = crop[:, : seam - 40]
    return np.clip(out.round(), 0, 255).astype(np.uint8)


def estimate_depth(img: np.ndarray) -> np.ndarray:
    import torch
    from transformers import AutoImageProcessor, AutoModelForDepthEstimation

    name = "depth-anything/Depth-Anything-V2-Large-hf"
    processor = AutoImageProcessor.from_pretrained(name)
    model = AutoModelForDepthEstimation.from_pretrained(name).eval()
    rgb = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    w, h = rgb.size
    scale = 518 / min(w, h)
    pw, ph = round(w * scale / 14) * 14, round(h * scale / 14) * 14
    inputs = processor(images=rgb, return_tensors="pt", size={"height": ph, "width": pw},
                       keep_aspect_ratio=False, do_resize=True)
    with torch.no_grad():
        pred = model(**inputs).predicted_depth
    pred = torch.nn.functional.interpolate(pred.unsqueeze(1), size=(h, w), mode="bicubic",
                                           align_corners=False)[0, 0].numpy()
    lo, hi = np.percentile(pred, 0.5), np.percentile(pred, 99.8)
    depth = np.clip((pred - lo) / (hi - lo), 0, 1).astype(np.float32)
    return cv2.bilateralFilter(depth, d=9, sigmaColor=0.06, sigmaSpace=4)


def build(src: Path, out_dir: Path) -> None:
    render = cv2.imread(str(src))
    if render is None or render.shape[:2] != (1357, 2400):
        sys.exit(f"{src}: expected the 2400×1357 source render")
    model = crop_and_pad(inpaint_pins(render))
    depth = estimate_depth(model)

    small = cv2.resize(depth, DEPTH_SIZE, interpolation=cv2.INTER_AREA)
    small = cv2.dilate(small, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
    small = cv2.GaussianBlur(small, (0, 0), 0.8)

    out_dir.mkdir(parents=True, exist_ok=True)
    Image.fromarray(cv2.cvtColor(model, cv2.COLOR_BGR2RGB)).save(
        out_dir / "officina-modello.webp", quality=90, method=6)
    Image.fromarray((small * 255).round().astype(np.uint8)).save(
        out_dir / "officina-profondita.webp", quality=90, method=6)


def constants(out_dir: Path) -> None:
    """Print hero-scene.ts's numbers, measured on the depth map as shipped."""
    w, h = Image.open(out_dir / "officina-modello.webp").size
    print(f"STAGE {{ width: {w}, height: {h} }}")
    depth = np.asarray(Image.open(out_dir / "officina-profondita.webp").convert("L"), np.float32) / 255
    dh, dw = depth.shape
    u = ((np.arange(dw) + 0.5) / dw)[None, :] * np.ones((dh, 1))
    v = ((np.arange(dh) + 0.5) / dh)[:, None] * np.ones((1, dw))
    x0, y0 = CROP[0], CROP[1]

    # Ground: the navy floor the model stands on. Seed the fit with the margin
    # outside the plinth's bounds, then refit on everything that is not model.
    far = np.ones((dh, dw), bool)
    px0, py0 = (800 - x0) / w, (104 - y0) / h
    px1, py1 = (2364 - x0) / w, (1230 - y0) / h
    far[int(py0 * dh) : int(py1 * dh), int(px0 * dw) : int(px1 * dw)] = False
    for _ in range(3):
        basis = np.stack([u[far], v[far], u[far] * v[far], v[far] ** 2, np.ones(far.sum())], 1)
        ground, *_ = np.linalg.lstsq(basis, depth[far], rcond=None)
        ground_map = ground[0] * u + ground[1] * v + ground[2] * u * v + ground[3] * v * v + ground[4]
        on_model = (depth - ground_map) > 0.04
        far = cv2.dilate(on_model.astype(np.uint8), np.ones((61, 61), np.uint8)) == 0
    print("DEPTH.ground", [round(float(c), 4) for c in ground])

    smooth = cv2.GaussianBlur(cv2.blur(depth, (6, 6)), (0, 0), 2.0)
    a, b, c = SCAN_AXIS
    s = a * u + b * v + c * smooth
    s_lo, s_hi = np.percentile(s[on_model], 0.5), np.percentile(s[on_model], 99.5)
    print(f"DEPTH.scanRange [{s_lo:.4f}, {s_hi:.4f}]")
    for name, (bu, bv) in LIVE_PINS.items():
        sn = (a * bu + b * bv + c * smooth[int(bv * dh), int(bu * dw)] - s_lo) / (s_hi - s_lo)
        print(f"{name:11s} base=({bu:.4f}, {bv:.4f}) scan={sn:.3f}")


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--constants":
        constants(Path(sys.argv[2]))
    elif len(sys.argv) == 3:
        build(Path(sys.argv[1]), Path(sys.argv[2]))
        constants(Path(sys.argv[2]))
    else:
        sys.exit(__doc__)
