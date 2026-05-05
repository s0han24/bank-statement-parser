import io
import sys
from dataclasses import dataclass

@dataclass
class NoisePreset:
    name:           str
    blur_radius:    float   = 0.0   # gaussian blur sigma
    grain_amount:   float   = 0.0   # std-dev of Gaussian noise (0-50)
    speckle_prob:   float   = 0.0   # probability each pixel flips (salt&pepper)
    skew_deg:       float   = 0.0   # max absolute rotation in degrees
    brightness_var: float   = 0.0   # +/- fraction of mean brightness shift
    stamp_alpha:    float   = 0.0   # 0 = no stamp
    watermark_alpha:float   = 0.0   # 0 = no watermark
    jpeg_quality:   int     = 95    # JPEG re-encode quality (95=lossless-ish)
    dpi:            int     = 200   # render DPI

PRESETS = {
    "clean": NoisePreset(name="clean", dpi=200),
    "light": NoisePreset(
        name="light", blur_radius=0.4, grain_amount=4, speckle_prob=0.001,
        skew_deg=0.3, brightness_var=0.05, stamp_alpha=0.0, watermark_alpha=0.08,
        jpeg_quality=92, dpi=200,
    ),
    "heavy": NoisePreset(
        name="heavy", blur_radius=1.0, grain_amount=12, speckle_prob=0.005,
        skew_deg=1.2, brightness_var=0.12, stamp_alpha=0.35, watermark_alpha=0.12,
        jpeg_quality=80, dpi=150,
    ),
}

def _pdf_to_images(pdf_bytes: bytes, dpi: int):
    try:
        import fitz
        from PIL import Image
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        imgs = []
        for page in doc:
            pix = page.get_pixmap(dpi=dpi)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            imgs.append(img)
        return imgs
    except Exception as e:
        print(f"  [warn] PDF rasterisation failed: {e}", file=sys.stderr)
        return []

def apply_noise(pdf_bytes: bytes, preset: NoisePreset, seed: int = 0) -> bytes:
    import numpy as np
    from PIL import Image, ImageFilter, ImageDraw

    rng_np = np.random.RandomState(seed)
    images = _pdf_to_images(pdf_bytes, preset.dpi)
    if not images:
        print("  [warn] PDF rasterisation unavailable — returning clean PDF", file=sys.stderr)
        return pdf_bytes

    output_buf = io.BytesIO()
    processed  = []

    for img in images:
        arr = np.array(img, dtype=np.float32)

        if preset.blur_radius > 0:
            img_pil = Image.fromarray(arr.clip(0,255).astype(np.uint8))
            img_pil = img_pil.filter(ImageFilter.GaussianBlur(radius=preset.blur_radius))
            arr = np.array(img_pil, dtype=np.float32)

        if preset.grain_amount > 0:
            noise = rng_np.normal(0, preset.grain_amount, arr.shape)
            arr   = arr + noise

        if preset.speckle_prob > 0:
            mask_salt   = rng_np.rand(*arr.shape[:2]) < preset.speckle_prob / 2
            mask_pepper = rng_np.rand(*arr.shape[:2]) < preset.speckle_prob / 2
            arr[mask_salt,   :] = 255
            arr[mask_pepper, :] = 0

        if preset.brightness_var > 0:
            shift = rng_np.uniform(-preset.brightness_var, preset.brightness_var)
            arr   = arr * (1 + shift)

        arr = arr.clip(0, 255).astype(np.uint8)
        img = Image.fromarray(arr)

        if preset.skew_deg > 0:
            angle = rng_np.uniform(-preset.skew_deg, preset.skew_deg)
            img   = img.rotate(angle, expand=False, fillcolor=(255, 255, 255))

        if preset.watermark_alpha > 0:
            W, H  = img.size
            overlay = Image.new("RGBA", (W, H), (255, 255, 255, 0))
            draw    = ImageDraw.Draw(overlay)
            text    = "CONFIDENTIAL"
            for yi in range(-H, H*2, int(H * 0.28)):
                draw.text((W // 4, yi), text, fill=(180, 0, 0, int(255 * preset.watermark_alpha)), font=None)
            wm_rot  = overlay.rotate(35, expand=False)
            img     = img.convert("RGBA")
            img     = Image.alpha_composite(img, wm_rot).convert("RGB")

        if preset.stamp_alpha > 0:
            draw  = ImageDraw.Draw(img)
            W, H  = img.size
            sw, sh = int(W * 0.18), int(H * 0.04)
            x0, y0 = W - sw - 20, H - sh - 20
            alpha  = int(255 * preset.stamp_alpha)
            overlay2 = Image.new("RGBA", img.size, (255,255,255,0))
            d2 = ImageDraw.Draw(overlay2)
            d2.rectangle([x0, y0, x0+sw, y0+sh], outline=(0, 80, 0, alpha), width=2)
            d2.text((x0 + 6, y0 + 4), "PROCESSED", fill=(0, 80, 0, alpha))
            img = Image.alpha_composite(img.convert("RGBA"), overlay2).convert("RGB")

        if preset.jpeg_quality < 95:
            tmp = io.BytesIO()
            img.save(tmp, format="JPEG", quality=preset.jpeg_quality)
            tmp.seek(0)
            img = Image.open(tmp).convert("RGB")

        processed.append(img)

    if processed:
        first  = processed[0]
        others = processed[1:]
        first.save(output_buf, format="PDF", save_all=True, append_images=others, resolution=preset.dpi)
        return output_buf.getvalue()

    return pdf_bytes
