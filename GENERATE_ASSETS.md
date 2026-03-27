# Generating Required SEO Assets

This guide explains how to create the image assets needed for optimal SEO and social media sharing.

## Quick Summary

You need to create these files in your web root:
- `screenshots/preview.png` – Open Graph preview image (1200×630px)
- `favicon-32x32.png` – Favicon (32×32px)
- `favicon-16x16.png` – Favicon (16×16px)
- `apple-touch-icon.png` – iOS home screen icon (180×180px)
- `logo.png` – Site logo (200×200px+)
- `site.webmanifest` – Web app manifest (already created in repo)

## Using Python to Generate Favicon Pack

Install required library:
```bash
pip install Pillow
```

Create a script `generate_favicon.py`:

```python
from PIL import Image, ImageDraw, ImageFont
import os

def create_favicon_set():
    """Generate a favicon set from a simple design."""

    # Create directories
    os.makedirs("screenshots", exist_ok=True)

    # Define colors (matching dark theme)
    COLORS = {
        "bg": "#0f0f13",
        "accent": "#60a5fa",  # Blue gradient
        "text": "#e8e8f0",
    }

    # 1. Generate 180×180 Apple Touch Icon
    img = Image.new("RGB", (180, 180), COLORS["bg"])
    draw = ImageDraw.Draw(img)

    # Draw simple fuel pump icon
    # Vertical pump handle: rect from (60, 60) to (120, 140)
    draw.rectangle([60, 60, 120, 140], fill=COLORS["accent"], outline=COLORS["text"])
    # Pump nozzle circle at bottom
    draw.ellipse([70, 140, 110, 180], fill=COLORS["accent"], outline=COLORS["text"])
    # Pump top circle
    draw.ellipse([70, 40, 110, 80], fill=COLORS["accent"])

    img.save("apple-touch-icon.png", "PNG")
    print("✓ apple-touch-icon.png (180×180)")

    # 2. Generate 32×32 Favicon
    img_32 = img.resize((32, 32), Image.Resampling.LANCZOS)
    img_32.save("favicon-32x32.png", "PNG")
    print("✓ favicon-32x32.png (32×32)")

    # 3. Generate 16×16 Favicon
    img_16 = img.resize((16, 16), Image.Resampling.LANCZOS)
    img_16.save("favicon-16x16.png", "PNG")
    print("✓ favicon-16x16.png (16×16)")

    # 4. Generate logo (200×200)
    img_logo = Image.new("RGB", (200, 200), COLORS["bg"])
    draw_logo = ImageDraw.Draw(img_logo)

    # Similar design but with more detail
    draw_logo.rectangle([50, 50, 150, 150], fill=COLORS["accent"], outline=COLORS["text"], width=2)
    draw_logo.text((75, 95), "⛽", fill=COLORS["text"])

    img_logo.save("logo.png", "PNG")
    print("✓ logo.png (200×200)")

if __name__ == "__main__":
    create_favicon_set()
    print("\n✓ All favicons generated!")
    print("\nPlace these files in your web root directory.")
```

Run it:
```bash
python3 generate_favicon.py
```

## Creating the Preview Image (1200×630px)

### Option 1: Using Python (Pillow)

```python
from PIL import Image, ImageDraw, ImageFont
import textwrap

def create_preview_image():
    """Create a 1200×630 Open Graph preview image."""

    img = Image.new("RGB", (1200, 630), color="#0f0f13")
    draw = ImageDraw.Draw(img)

    # Try to use system fonts, fallback to default
    try:
        title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 60)
        subtitle_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 32)
    except:
        title_font = ImageFont.load_default()
        subtitle_font = ImageFont.load_default()

    # Add gradient-like effect (simple colored blocks)
    draw.rectangle([0, 0, 1200, 630], fill="#0f0f13")
    draw.rectangle([0, 0, 1200, 150], fill="#1a1a24")

    # Add emoji and text
    text_y = 180
    draw.text((600, text_y), "⛽ BilligTanken",
             font=title_font, fill="#60a5fa", anchor="mm")

    draw.text((600, text_y + 100), "Günstigste Tankstellen in Österreich",
             font=subtitle_font, fill="#a78bfa", anchor="mm")

    # Add some statistics placeholder
    draw.text((600, text_y + 180), "Echtzeit-Preise • GPS-Navigation • Top Stationen",
             font=subtitle_font, fill="#e8e8f0", anchor="mm")

    img.save("screenshots/preview.png", "PNG")
    print("✓ screenshots/preview.png (1200×630)")

if __name__ == "__main__":
    import os
    os.makedirs("screenshots", exist_ok=True)
    create_preview_image()
```

### Option 2: Using ImageMagick

```bash
convert -size 1200x630 xc:'#0f0f13' \
  -fill '#60a5fa' -pointsize 80 \
  -gravity center -annotate +0+50 '⛽ BilligTanken' \
  -fill '#a78bfa' -pointsize 40 \
  -gravity center -annotate +0+150 'Günstigste Tankstellen in Österreich' \
  screenshots/preview.png
```

### Option 3: Use an Online Tool

Use Canva, Figma, or similar to create:
- Size: 1200×630px
- Background: Dark theme color (#0f0f13)
- Include: Logo, title "BilligTanken", tagline
- Add: fuel pump emoji or icon
- Use brand colors: #60a5fa, #a78bfa, #34d399

## Installation in Docker

If using Docker, copy files to your build directory:

```dockerfile
# In Dockerfile
COPY apple-touch-icon.png /var/www/localhost/htdocs/
COPY favicon-32x32.png /var/www/localhost/htdocs/
COPY favicon-16x16.png /var/www/localhost/htdocs/
COPY logo.png /var/www/localhost/htdocs/
COPY site.webmanifest /var/www/localhost/htdocs/
COPY screenshots/preview.png /var/www/localhost/htdocs/screenshots/
```

Or using volumes in docker-compose.yml:

```yaml
volumes:
  - ./apple-touch-icon.png:/var/www/localhost/htdocs/apple-touch-icon.png
  - ./favicon-32x32.png:/var/www/localhost/htdocs/favicon-32x32.png
  - ./favicon-16x16.png:/var/www/localhost/htdocs/favicon-16x16.png
  - ./logo.png:/var/www/localhost/htdocs/logo.png
  - ./site.webmanifest:/var/www/localhost/htdocs/site.webmanifest
  - ./screenshots/preview.png:/var/www/localhost/htdocs/screenshots/preview.png
```

## File Checklist

After generation, verify your files:

```bash
# Check all required files exist
ls -lh apple-touch-icon.png       # ~180×180px
ls -lh favicon-32x32.png          # 32×32px
ls -lh favicon-16x16.png          # 16×16px
ls -lh logo.png                   # 200×200px
ls -lh screenshots/preview.png    # 1200×630px
ls -lh site.webmanifest           # JSON file

# Test with a web server
python3 -m http.server 8000

# Then visit:
# http://localhost:8000/
# Check browser console for any 404 errors on favicons
```

## Testing Social Media

After uploading, test how your page appears when shared:

1. **Facebook**: https://developers.facebook.com/tools/debug/sharing/
   - Paste your URL and click "Debug"
   - Check preview image and description
   - Click "Scrape Again" to refresh cache

2. **Twitter**: https://cards-dev.twitter.com/validator
   - Enter your URL
   - Preview card appearance

3. **LinkedIn**: Share the URL and preview in editor

## Optimization Tips

- **Preview Image**: Use high contrast colors for visibility at small sizes
- **Favicon**: Test at actual size (16×16, 32×32) to ensure readability
- **Logo**: Keep padding around edges for better appearance
- **Format**: Use PNG for lossless quality, JPG for smaller file sizes
- **Size**: Optimize images with tools like TinyPNG or ImageOptim to reduce bandwidth

## Troubleshooting

**Icon not showing?**
- Clear browser cache (Ctrl+Shift+Delete)
- Check file paths are absolute in HTML
- Verify file permissions (should be readable)

**Wrong image on social media?**
- Wait 24 hours for cache to clear
- Use Facebook/Twitter debuggers to force refresh
- Check og:image URL is accessible and returns correct image

**Web manifest not loading?**
- Verify file is served with correct MIME type: `application/manifest+json`
- Add to Apache: `AddType application/manifest+json webmanifest`

## Resources

- [Open Graph Protocol](https://ogp.me/)
- [Twitter Card Documentation](https://developer.twitter.com/en/docs/twitter-for-websites/cards/overview/abouts-cards)
- [Web App Manifest](https://www.w3.org/TR/appmanifest/)
- [Favicon Best Practices](https://favicon.io/)
- [Schema.org LocalBusiness](https://schema.org/LocalBusiness)
