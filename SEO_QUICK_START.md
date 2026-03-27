# SEO Quick Start Guide

## What Changed?

Enhanced your HTML with professional SEO and social media meta tags. The code is fully backward compatible—existing scripts work unchanged.

## The 5-Minute Setup

### 1. Generate Images (Optional but Recommended)
```bash
pip install Pillow
python3 generate_seo_assets.py
```

This creates:
- 🖼️ `screenshots/preview.png` (1200×630) – For social media
- 🎨 `apple-touch-icon.png` (180×180) – iOS home screen
- 🔗 Favicons (32×32, 16×16)
- 📋 `logo.png` (200×200)

### 2. Enable Absolute URLs (For Social Media)
Edit your script (e.g., `billigtanken-vorarlberg.py`):

```python
# Add your domain (or env variable)
html = generate_html(
    ...,
    base_url="https://billigtanken.at"  # ← Add this
)
```

Or use environment variable in Docker:
```yaml
environment:
  BASE_URL: https://billigtanken.at
```

### 3. Deploy & Test
```bash
docker compose up -d --build
```

Test with these free tools:
- Facebook: https://developers.facebook.com/tools/debug/
- Twitter: https://cards-dev.twitter.com/validator
- Google: https://search.google.com/test/rich-results

## What You Get

| Feature | Benefit |
|---------|---------|
| 📱 Open Graph | Proper previews on Facebook, LinkedIn, Pinterest |
| 🐦 Twitter Card | Rich previews on Twitter/X |
| 🔍 Schema.org | Better Google search visibility |
| 🏠 PWA Support | Installable as app on mobile |
| 🎯 Structured Data | Rich snippets in search results |
| 🌐 Mobile | Optimized for all devices |

## The Code Changes

### In `billigtanken_lib.py`:

**Added:**
```html
<!-- Open Graph -->
<meta property="og:title" content="..." />
<meta property="og:description" content="..." />
<meta property="og:image" content="..." />
<meta property="og:url" content="..." />

<!-- Twitter Card -->
<meta name="twitter:card" content="summary_large_image" />
<meta name="twitter:image" content="..." />

<!-- JSON-LD Schema -->
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "LocalBusiness",
  ...
}
</script>

<!-- PWA Support -->
<meta name="theme-color" content="#0f0f13" />
<link rel="manifest" href="/site.webmanifest" />
<link rel="apple-touch-icon" href="/apple-touch-icon.png" />
```

**Function signature updated:**
```python
def generate_html(..., base_url: str = "")
```

All parameters optional—backward compatible! ✓

## Default Behavior (No Changes Needed)

If you don't change anything:
- ✓ Works exactly as before
- ✓ All new meta tags included
- ✓ Images use relative paths
- ✓ Suitable for local/intranet deployment

## For Public Deployment

To get the best social media sharing experience:

1. **Set `base_url`** in your scripts:
   ```python
   base_url = os.environ.get("BASE_URL", "")
   ```

2. **Generate images**:
   ```bash
   python3 generate_seo_assets.py
   ```

3. **Copy files to web root**:
   ```bash
   cp apple-touch-icon.png /var/www/html/
   cp favicon-*.png /var/www/html/
   cp logo.png /var/www/html/
   cp site.webmanifest /var/www/html/
   cp -r screenshots /var/www/html/
   ```

4. **For Docker**, add to docker-compose.yml:
   ```yaml
   environment:
     BASE_URL: https://your-domain.at
   volumes:
     - ./apple-touch-icon.png:/var/www/localhost/htdocs/apple-touch-icon.png
     - ./favicon-32x32.png:/var/www/localhost/htdocs/favicon-32x32.png
     - ./site.webmanifest:/var/www/localhost/htdocs/site.webmanifest
   ```

## Files Added

```
SEO_IMPROVEMENTS.md          ← Complete documentation
GENERATE_ASSETS.md           ← How to create images
SEO_QUICK_START.md          ← This file
generate_seo_assets.py       ← Auto-generate images
site.webmanifest            ← Web app manifest (customize)
```

## Testing Checklist

- [ ] Run `docker compose up -d --build`
- [ ] Visit `http://localhost:8080` in browser
- [ ] Check browser DevTools → Application → Manifest (should load)
- [ ] Test on Facebook Debugger
- [ ] Test on Twitter Card Validator
- [ ] Check Google Rich Results Test
- [ ] Test on mobile device (PWA installation)

## Common Questions

**Q: Do I need to change anything?**
A: No, everything works as-is. Changes are optional for social media optimization.

**Q: Where do the image files go?**
A: Web root directory (where index.html is served from):
- `apple-touch-icon.png` – root
- `favicon-*.png` – root
- `logo.png` – root
- `screenshots/preview.png` – in screenshots/ subdirectory
- `site.webmanifest` – root

**Q: What if I'm serving from `/var/www/localhost/htdocs`?**
A: For Docker, use volume mounts in docker-compose.yml (see example above).

**Q: Does this affect performance?**
A: No, meta tags add <2KB of HTML. Zero JavaScript overhead.

**Q: Can I use my own images?**
A: Yes! Replace the generated files with your own:
- Preview image: 1200×630px PNG
- Favicons: 32×32 and 16×16 PNG
- Logo: 200×200+ PNG
- Keep the same filenames and paths

**Q: How do I customize the manifest?**
A: Edit `site.webmanifest` to change app name, colors, icons, etc.

## Next Steps

1. **Immediate**: Everything works now. No action needed.
2. **Optional**: Run `python3 generate_seo_assets.py` to create images
3. **For public site**: Set `base_url` and copy assets to web root
4. **Test**: Use the validators above to verify everything works
5. **Monitor**: Check Google Search Console for indexing status

## More Information

See detailed docs:
- `SEO_IMPROVEMENTS.md` – Full feature list
- `GENERATE_ASSETS.md` – Image generation guide
- `site.webmanifest` – Manifest configuration options

---

**Questions?** Check the main documentation files or run:
```bash
python3 generate_seo_assets.py --help  # (will add in next update)
```
