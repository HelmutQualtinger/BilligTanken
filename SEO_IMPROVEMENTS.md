# SEO & Social Media Improvements

## Overview
Enhanced meta tags and structured data have been added to improve search engine indexing and social media preview rendering.

## What's New

### 1. **Open Graph Tags** (Facebook, LinkedIn, Pinterest)
- `og:title` – Social media title
- `og:description` – Social media description
- `og:image` – Preview image (1200×630px recommended)
- `og:type` – Content type (website)
- `og:url` – Canonical URL (when base_url is provided)
- `og:locale` – Locale setting (de_AT)
- `og:site_name` – Site name

### 2. **Twitter Card Tags**
- `twitter:card` – Card type (summary_large_image)
- `twitter:title` – Tweet title
- `twitter:description` – Tweet description
- `twitter:image` – Tweet image

### 3. **SEO Meta Tags**
- `robots` – Search engine directives (index, follow, image preview)
- `author` – Author attribution
- `keywords` – Search keywords
- `language` – Language specification (de, de-AT)

### 4. **Mobile & PWA Support**
- `theme-color` – Browser address bar color
- `color-scheme` – Light/dark mode support
- `apple-mobile-web-app-capable` – Installable as app
- `apple-mobile-web-app-status-bar-style` – Status bar styling
- `apple-touch-icon` – Home screen icon
- Favicon links (32×32, 16×16)
- Web manifest (`site.webmanifest`)

### 5. **Structured Data (JSON-LD)**
LocalBusiness schema for:
- Business name, description, URL
- Logo and image
- Address and region information
- Search engine understanding

## How to Use

### Basic Usage (Default)
```bash
python3 billigtanken-vorarlberg.py
```
Uses relative URLs for images. Works fine for serving on a single domain.

### With Absolute URLs (Recommended for Social Media)
Update your script to pass `base_url`:

```python
html = generate_html(
    stations_sup, stations_die, fetched_at,
    HOME_LAT, HOME_LON, HOME_NAME,
    TITLE, META_DESCRIPTION, META_KEYWORDS,
    OG_TITLE, OG_DESCRIPTION,
    H1, SUB_SUP, SUB_DIE,
    base_url="https://billigtanken.at"  # Add this line
)
```

### Docker Setup
If serving behind a reverse proxy, set the domain in your script:

```bash
# In billigtanken-vorarlberg.py
BASE_URL = os.environ.get("BASE_URL", "https://billigtanken.at")

html = generate_html(
    ...,
    base_url=BASE_URL
)
```

Then in docker-compose.yml:
```yaml
environment:
  BASE_URL: https://billigtanken.at
```

## Required Assets

For full functionality, create these files in your web root:

### 1. **Preview Image** (`screenshots/preview.png`)
- Size: 1200×630px (for Open Graph)
- Format: PNG
- Example: Screenshot of the website showing top gas prices

### 2. **Favicon**
- `favicon-32x32.png` – 32×32px
- `favicon-16x16.png` – 16×16px
- `apple-touch-icon.png` – 180×180px

### 3. **Logo** (`logo.png`)
- For JSON-LD schema
- Recommended: 200×200px or larger
- SVG or PNG

### 4. **Web Manifest** (`site.webmanifest`)
```json
{
  "name": "BilligTanken",
  "short_name": "BilligTanken",
  "description": "Günstigste Tankstellen in Österreich",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#0f0f13",
  "theme_color": "#0f0f13",
  "orientation": "portrait-primary",
  "icons": [
    {
      "src": "/favicon-32x32.png",
      "sizes": "32x32",
      "type": "image/png"
    },
    {
      "src": "/apple-touch-icon.png",
      "sizes": "180x180",
      "type": "image/png"
    }
  ]
}
```

## Testing Your SEO

### 1. **Facebook Sharing Debugger**
https://developers.facebook.com/tools/debug/sharing/

### 2. **Twitter Card Validator**
https://cards-dev.twitter.com/validator

### 3. **Google Rich Results Test**
https://search.google.com/test/rich-results

### 4. **Schema.org Validator**
https://validator.schema.org/

## Performance Considerations

- Meta tags add minimal overhead (~2KB)
- JSON-LD structured data helps with SEO
- All tags are HTML standards-compliant
- No JavaScript dependencies
- Works with dark/light theme switching

## Backward Compatibility

All changes are backward compatible:
- Existing scripts continue to work without modification
- `base_url` parameter is optional (defaults to empty string)
- Relative URLs work fine if not providing base_url
- New meta tags don't break any existing functionality

## Next Steps

1. Create the required image assets (preview.png, favicon, logo)
2. Create site.webmanifest file
3. Update scripts to pass `base_url` if serving on a public domain
4. Test with the validators listed above
5. Monitor Google Search Console for indexing
