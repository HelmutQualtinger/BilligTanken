#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate SEO assets: favicons, logo, and preview image.
Requires: pip install Pillow
"""

import os
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("ERROR: Pillow not installed. Run: pip install Pillow")
    sys.exit(1)

# Colors from the theme
COLORS = {
    "bg": "#0f0f13",
    "text": "#e8e8f0",
    "accent_blue": "#60a5fa",
    "accent_purple": "#a78bfa",
    "accent_green": "#34d399",
}

def create_directories():
    """Create required directories."""
    os.makedirs("screenshots", exist_ok=True)
    print("✓ Directories created")

def draw_fuel_pump(draw, x, y, size, color, outline_color):
    """Helper to draw a simple fuel pump icon."""
    # Pump handle (vertical rectangle)
    handle_width = size // 4
    handle_height = size // 2
    draw.rectangle(
        [x - handle_width // 2, y, x + handle_width // 2, y + handle_height],
        fill=color, outline=outline_color, width=2
    )
    # Pump nozzle (circle at bottom)
    nozzle_size = size // 3
    draw.ellipse(
        [x - nozzle_size // 2, y + handle_height, x + nozzle_size // 2, y + handle_height + nozzle_size],
        fill=color, outline=outline_color, width=2
    )

def create_apple_touch_icon():
    """Generate 180×180 Apple touch icon."""
    size = 180
    img = Image.new("RGB", (size, size), COLORS["bg"])
    draw = ImageDraw.Draw(img)

    # Draw fuel pump
    draw_fuel_pump(draw, size // 2, size // 4, size // 2, COLORS["accent_blue"], COLORS["text"])

    img.save("apple-touch-icon.png", "PNG")
    print(f"✓ apple-touch-icon.png ({size}×{size})")

def create_favicon_32():
    """Generate 32×32 favicon."""
    size = 32
    img = Image.new("RGB", (size, size), COLORS["bg"])
    draw = ImageDraw.Draw(img)

    # Simplified pump for small size
    # Just a vertical bar with a circle
    draw.rectangle([12, 8, 20, 24], fill=COLORS["accent_blue"])
    draw.ellipse([10, 24, 22, 32], fill=COLORS["accent_blue"])

    img.save("favicon-32x32.png", "PNG")
    print(f"✓ favicon-32x32.png ({size}×{size})")

def create_favicon_16():
    """Generate 16×16 favicon."""
    size = 16
    img = Image.new("RGB", (size, size), COLORS["bg"])
    draw = ImageDraw.Draw(img)

    # Minimal pump for tiny icon
    draw.rectangle([6, 4, 10, 12], fill=COLORS["accent_blue"])
    draw.ellipse([5, 12, 11, 16], fill=COLORS["accent_blue"])

    img.save("favicon-16x16.png", "PNG")
    print(f"✓ favicon-16x16.png ({size}×{size})")

def create_logo():
    """Generate 200×200 logo."""
    size = 200
    img = Image.new("RGB", (size, size), COLORS["bg"])
    draw = ImageDraw.Draw(img)

    # Draw border
    border = 10
    draw.rectangle(
        [border, border, size - border, size - border],
        outline=COLORS["accent_blue"], width=3
    )

    # Draw fuel pump icon
    draw_fuel_pump(
        draw, size // 2, size // 4, size // 2,
        COLORS["accent_blue"], COLORS["accent_purple"]
    )

    img.save("logo.png", "PNG")
    print(f"✓ logo.png ({size}×{size})")

def create_preview_image():
    """Generate 1200×630 Open Graph preview image."""
    width, height = 1200, 630
    img = Image.new("RGB", (width, height), COLORS["bg"])
    draw = ImageDraw.Draw(img)

    # Draw gradient-like background effect (colored sections)
    draw.rectangle([0, 0, width, 150], fill="#1a1a24")
    draw.rectangle([0, 150, width, 200], fill="#22222f")

    # Try to load a nice font
    title_size = 80
    subtitle_size = 48
    small_size = 36

    try:
        # Try to load system fonts
        title_font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", title_size
        )
        subtitle_font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", subtitle_size
        )
        small_font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", small_size
        )
    except (OSError, AttributeError):
        # Fallback to default font if system fonts not available
        print("  (Using default font - install fonts for better look)")
        title_font = ImageFont.load_default()
        subtitle_font = ImageFont.load_default()
        small_font = ImageFont.load_default()

    # Main title with emoji
    title = "⛽ BilligTanken"
    draw.text(
        (width // 2, 120),
        title,
        font=title_font,
        fill=COLORS["accent_blue"],
        anchor="mm"
    )

    # Subtitle
    subtitle = "Günstigste Tankstellen"
    draw.text(
        (width // 2, 260),
        subtitle,
        font=subtitle_font,
        fill=COLORS["accent_purple"],
        anchor="mm"
    )

    # Additional info
    info = "Echtzeit-Preise • GPS-Navigation • Top Stationen"
    draw.text(
        (width // 2, 400),
        info,
        font=small_font,
        fill=COLORS["text"],
        anchor="mm"
    )

    # Source attribution at bottom
    draw.text(
        (width // 2, height - 50),
        "Datenquelle: E-Control Austria",
        font=small_font,
        fill=COLORS["accent_green"],
        anchor="mm"
    )

    img.save("screenshots/preview.png", "PNG")
    print(f"✓ screenshots/preview.png ({width}×{height})")

def verify_files():
    """Verify all files were created."""
    files = [
        "apple-touch-icon.png",
        "favicon-32x32.png",
        "favicon-16x16.png",
        "logo.png",
        "screenshots/preview.png",
    ]

    missing = []
    for f in files:
        if not Path(f).exists():
            missing.append(f)

    if missing:
        print(f"\n⚠ Missing files: {', '.join(missing)}")
        return False

    print("\n✓ All assets created successfully!")
    return True

def main():
    """Main entry point."""
    print("BilligTanken SEO Asset Generator")
    print("=" * 50)

    try:
        create_directories()
        print("\nGenerating assets...")
        create_apple_touch_icon()
        create_favicon_32()
        create_favicon_16()
        create_logo()
        create_preview_image()

        if verify_files():
            print("\n📍 Next steps:")
            print("1. Copy files to your web root directory")
            print("2. For Docker: see docker-compose.yml volume mounts")
            print("3. Test with: https://developers.facebook.com/tools/debug/")
            print("4. See SEO_IMPROVEMENTS.md for more info")
        else:
            sys.exit(1)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
