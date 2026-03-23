# Brand Logo Finder

Given a brand name (e.g. a fuel station brand), find the best available logo URL by querying multiple public APIs in order of quality.

## Usage

```
/brand-logo <brand name>
```

Examples:
- `/brand-logo OMV`
- `/brand-logo Diskont`
- `/brand-logo Leitner`

## Your Task

1. **Determine the domain** for the brand:
   - Check `BRAND_DOMAINS` in `billigtanken.py` first — it may already be there
   - If not, infer the likely domain (e.g. `omv.at`, `jet-tankstellen.at`) or search the web for the brand's official website

2. **Try each logo source** in this priority order using WebFetch (HEAD or GET) to check if the URL returns a valid image (HTTP 200, content-type image/*):

   | Priority | Source | URL pattern |
   |----------|--------|-------------|
   | 1 | **Clearbit Logo API** | `https://logo.clearbit.com/{domain}` |
   | 2 | **Google Favicon (128px)** | `https://www.google.com/s2/favicons?domain={domain}&sz=128` |
   | 3 | **DuckDuckGo Favicon** | `https://icons.duckduckgo.com/ip3/{domain}.ico` |
   | 4 | **Wikimedia Commons** | Search `https://commons.wikimedia.org/w/api.php?action=query&titles=File:{Brand}_logo.svg&prop=imageinfo&iiprop=url&format=json` |
   | 5 | **Brand's own /favicon.ico** | `https://{domain}/favicon.ico` |

3. **Report results** in a table:

   ```
   Brand: OMV
   Domain: omv.at

   Source            | URL                                          | Status
   ------------------|----------------------------------------------|-------
   Clearbit          | https://logo.clearbit.com/omv.at             | ✓ 200
   Google Favicon    | https://www.google.com/s2/favicons?...       | ✓ 200
   DuckDuckGo        | https://icons.duckduckgo.com/ip3/omv.at.ico  | ✓ 200
   Wikimedia         | https://upload.wikimedia.org/...             | ✓ 200
   Own favicon       | https://omv.at/favicon.ico                   | ✓ 200

   Best logo: https://logo.clearbit.com/omv.at  (Clearbit — highest quality)
   ```

4. **Offer to update `billigtanken.py`**:
   - If the brand is not yet in `BRAND_DOMAINS`, ask whether to add it
   - If a better URL exists than the current one (e.g. Clearbit vs Google Favicon), suggest updating `brand_logo_url()`
   - Use the Edit tool to apply changes if confirmed

## Notes

- Clearbit returns a clean square PNG at ~200px — best for UI
- Google Favicon is reliable but small (128px max)
- DuckDuckGo is a good fallback, returns .ico
- For Austrian regional brands (Diskont, Avanti, Leitner, Fuchs, Gutmann) Clearbit often works if the correct `.at` domain is used
- If all sources fail, suggest using initials fallback (already built into the code)
- Always prefer `.at` domains for Austrian brands over `.de` or `.com`
