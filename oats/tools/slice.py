#!/usr/bin/env python3
"""slice.py - cut the brand mockups into the web image set.

Reads content/images.json, crops each slot out of its source mockup and writes
static/img/<name>-<width>.{avif,webp,jpg} plus static/img/manifest.json, which the
templates' picture macro reads for srcset, intrinsic size and the sampled background.

The outputs are committed. The server never runs this - deploy is a git pull - so Pillow is
a dev dependency only. Run it again after a photo shoot: swap the `src`/`box` entries and the
site picks up the new files unchanged.

    python -m oats images            # everything
    python -m oats images --only hero-bowl
"""
import json
import os
import sys

from PIL import Image, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Quality settings are tuned for food: AVIF/WebP keep gloss and gradients without banding
# at these sizes; JPEG is the fallback for browsers that take neither.
AVIF_Q, WEBP_Q, JPG_Q = 62, 80, 84


def _hex(rgb):
    return "#%02x%02x%02x" % tuple(rgb[:3])


def sample(im, xy):
    """Average colour of a small patch, so one stray pixel cannot pick the background."""
    x, y = xy
    patch = im.crop((x, y, x + 6, y + 6)).convert("RGB")
    px = list(patch.getdata())
    return _hex([sum(c[i] for c in px) // len(px) for i in range(3)])


def pad(im, ratio, colour):
    """Centre `im` on a canvas of aspect `ratio` (w, h) filled with `colour`."""
    rw, rh = ratio
    w, h = im.size
    if w / h > rw / rh:
        nw, nh = w, round(w * rh / rw)
    else:
        nw, nh = round(h * rw / rh), h
    canvas = Image.new("RGB", (nw, nh), colour)
    canvas.paste(im, ((nw - w) // 2, (nh - h) // 2))
    return canvas


def resize(im, width):
    w, h = im.size
    if width == w:
        return im
    height = max(1, round(h * width / w))
    out = im.resize((width, height), Image.LANCZOS)
    if width > w:
        # Upscales from the mockups are soft; a light unsharp mask gets the edge back
        # without the halo you get from sharpening a downscale.
        out = out.filter(ImageFilter.UnsharpMask(radius=1.2, percent=70, threshold=2))
    return out


def write_variants(im, name, width, out_dir, avif_ok):
    im = im.convert("RGB")
    base = os.path.join(out_dir, f"{name}-{width}")
    formats = []
    if avif_ok:
        im.save(base + ".avif", quality=AVIF_Q, speed=4)
        formats.append("avif")
    im.save(base + ".webp", quality=WEBP_Q, method=6)
    formats.append("webp")
    im.save(base + ".jpg", quality=JPG_Q, optimize=True, progressive=True)
    formats.append("jpg")
    return formats


def run(only=None, log=print):
    from PIL import features
    avif_ok = features.check("avif")
    if not avif_ok:
        log("note: this Pillow has no AVIF encoder - writing WebP + JPEG only", flush=True)

    spec = json.load(open(os.path.join(ROOT, "content", "images.json")))
    src_dir = os.path.join(ROOT, spec["sources_dir"])
    out_dir = os.path.join(ROOT, spec["out_dir"])
    os.makedirs(out_dir, exist_ok=True)
    manifest_path = os.path.join(out_dir, "manifest.json")
    manifest = json.load(open(manifest_path)) if os.path.exists(manifest_path) else {}

    sources = {}
    for slot in spec["slots"]:
        if only and slot["name"] != only:
            continue
        src = slot["src"]
        if src not in sources:
            sources[src] = Image.open(os.path.join(src_dir, src)).convert("RGB")
        im = sources[src]
        crop = im.crop(tuple(slot["box"]))
        for box in slot.get("erase", []):
            # Mockup captions sit on flat colour; painting the sampled background over them
            # is cleaner than cropping around them. Boxes are in source coordinates.
            x0, y0 = slot["box"][0], slot["box"][1]
            colour = sample(im, slot.get("bg_sample", (box[0], box[1])))
            crop.paste(colour, (box[0] - x0, box[1] - y0, box[2] - x0, box[3] - y0))
        if "pad_to" in slot:
            # Some mockup cards are wider than 4:3. Padding with the card's own flat
            # background keeps every card the same shape without cropping a bowl.
            crop = pad(crop, slot["pad_to"], sample(im, slot["bg_sample"]))
        widths = slot["widths"]
        if widths[0] > crop.width:
            raise SystemExit(f"{slot['name']}: display width {widths[0]} exceeds crop width {crop.width}")
        formats = None
        for w in widths:
            formats = write_variants(resize(crop, w), slot["name"], w, out_dir, avif_ok)
        one_x = resize(crop, widths[0])
        entry = {
            "alt": slot["alt"],
            "width": one_x.width,
            "height": one_x.height,
            "widths": widths,
            "formats": formats,
        }
        if "bg_sample" in slot:
            entry["bg"] = sample(im, slot["bg_sample"])
        manifest[slot["name"]] = entry
        log(f"  {slot['name']:36s} {one_x.width}x{one_x.height}  x{len(widths)}  {' '.join(formats)}", flush=True)

    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=1, sort_keys=True)
        f.write("\n")
    log(f"wrote {len(manifest)} slots -> {os.path.relpath(manifest_path, ROOT)}", flush=True)


if __name__ == "__main__":
    only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
    run(only)
