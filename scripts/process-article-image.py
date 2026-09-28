#!/usr/bin/env python3
"""
SmartGearPick — Article Image Processing Pipeline
Automatically produces standard 1200x800 Progressive JPEGs with zero ICC/EXIF metadata.

Usage:
    python scripts/process-article-image.py <source_image_or_url> <slug>

Example:
    python scripts/process-article-image.py "C:/Downloads/new-headphones.png" "best-noise-cancelling-earbuds"
"""

import sys
import os
import urllib.request
import io
from PIL import Image

TARGET_WIDTH = 1200
TARGET_HEIGHT = 800
TARGET_RATIO = TARGET_WIDTH / TARGET_HEIGHT  # 1.5

def verify_jpeg(file_path):
    with open(file_path, 'rb') as f:
        data = f.read()

    is_soi = (data[0] == 0xFF and data[1] == 0xD8)
    if not is_soi:
        return False, "Not a valid JPEG (missing SOI marker)"

    offset = 2
    is_progressive = False
    has_icc = False
    has_exif = False
    width, height, channels = 0, 0, 0

    while offset < len(data) - 1:
        if data[offset] == 0xFF:
            marker = data[offset + 1]
            if marker == 0xD9 or marker == 0xDA:  # EOI or SOS
                break
            if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                length = int.from_bytes(data[offset+2:offset+4], 'big')
                height = int.from_bytes(data[offset+5:offset+7], 'big')
                width = int.from_bytes(data[offset+7:offset+9], 'big')
                channels = data[offset+9]
                if marker == 0xC2:
                    is_progressive = True
                offset += 2 + length
                continue
            if marker == 0xE1:  # APP1 (EXIF)
                length = int.from_bytes(data[offset+2:offset+4], 'big')
                app1_str = data[offset+4:offset+8]
                if app1_str.startswith(b'Exif'):
                    has_exif = True
                offset += 2 + length
                continue
            if marker == 0xE2:  # APP2 (ICC)
                length = int.from_bytes(data[offset+2:offset+4], 'big')
                app2_str = data[offset+4:offset+15]
                if app2_str.startswith(b'ICC_PROFILE'):
                    has_icc = True
                offset += 2 + length
                continue
            if 0xE0 <= marker <= 0xEF or marker in (0xDB, 0xC4):
                length = int.from_bytes(data[offset+2:offset+4], 'big')
                offset += 2 + length
                continue
        offset += 1

    checks = [
        (width == TARGET_WIDTH and height == TARGET_HEIGHT, f"Dimensions: {width}x{height} (expected {TARGET_WIDTH}x{TARGET_HEIGHT})"),
        (channels == 3, f"Channels: {channels} (expected 3 RGB)"),
        (is_progressive, f"Progressive JPEG (SOF2 0xC2): {is_progressive}"),
        (not has_icc, f"ICC Profile embedded: {has_icc} (must be False)"),
        (not has_exif, f"EXIF metadata embedded: {has_exif} (must be False)"),
        (len(data) < 250 * 1024, f"File size: {len(data):,} bytes (must be < 256,000 bytes)")
    ]

    all_ok = all(c[0] for c in checks)
    return all_ok, checks

def process_image(source, slug, output_dir=None):
    if output_dir is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        repo_root = os.path.dirname(script_dir)
        output_dir = os.path.join(repo_root, "assets", "images", "articles")

    os.makedirs(output_dir, exist_ok=True)
    clean_slug = slug.replace('.jpg', '').replace('.png', '').replace('.html', '').strip()
    target_path = os.path.join(output_dir, f"{clean_slug}.jpg")

    # 1. Load source image
    if source.startswith("http://") or source.startswith("https://"):
        print(f"[*] Downloading source image from URL: {source}")
        req = urllib.request.Request(source, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        with urllib.request.urlopen(req) as resp:
            img_bytes = resp.read()
        img = Image.open(io.BytesIO(img_bytes))
    else:
        if not os.path.isfile(source):
            print(f"[!] Error: Source file not found at {source}")
            sys.exit(1)
        img = Image.open(source)

    # 2. Convert to RGB (handle RGBA, CMYK, Palette, Grayscale)
    if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
        alpha_img = img.convert('RGBA')
        bg = Image.new('RGB', alpha_img.size, (255, 255, 255))
        bg.paste(alpha_img, mask=alpha_img.split()[3])
        img = bg
    elif img.mode != 'RGB':
        img = img.convert('RGB')

    # 3. Subject-aware Crop to 1.5 Aspect Ratio (3:2)
    src_w, src_h = img.size
    src_ratio = src_w / src_h

    if abs(src_ratio - TARGET_RATIO) > 0.001:
        if src_ratio > TARGET_RATIO:
            # Source is wider than 3:2 -> crop left/right
            new_w = int(src_h * TARGET_RATIO)
            left = (src_w - new_w) // 2
            img = img.crop((left, 0, left + new_w, src_h))
        else:
            # Source is taller than 3:2 -> crop top/bottom (center bias)
            new_h = int(src_w / TARGET_RATIO)
            top = (src_h - new_h) // 2
            img = img.crop((0, top, src_w, top + new_h))

    # 4. Resize to exactly 1200x800
    img = img.resize((TARGET_WIDTH, TARGET_HEIGHT), Image.Resampling.LANCZOS)

    # 5. Save as Progressive JPEG, optimize, quality=85 (No ICC, No EXIF)
    img.save(
        target_path,
        format='JPEG',
        quality=85,
        progressive=True,
        optimize=True
    )

    # 6. Verify binary
    ok, details = verify_jpeg(target_path)
    file_size = os.path.getsize(target_path)

    print("\n=======================================================")
    print(f" SMARTGEARPICK ARTICLE IMAGE PROCESSED SUCCESSFULLY")
    print("=======================================================")
    print(f" Output File:  {target_path}")
    print(f" Target URL:   https://smartgearpick.com/assets/images/articles/{clean_slug}.jpg")
    print(f" File Size:    {file_size:,} bytes ({file_size / 1024:.1f} KB)")
    print(f" Binary Check: {'PASSED [OK]' if ok else 'FAILED [ERROR]'}")
    print("-------------------------------------------------------")
    for passed, msg in details:
        status_sym = "[OK]" if passed else "[FAIL]"
        print(f"  {status_sym} {msg}")
    print("=======================================================\n")

    if not ok:
        sys.exit(1)

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python scripts/process-article-image.py <source_image_or_url> <slug>")
        sys.exit(1)
    process_image(sys.argv[1], sys.argv[2])
