# SmartGearPick — Article & Social Image Production Standards

This document defines the mandatory, automated standard for all article images and social metadata across **SmartGearPick.com**.

---

## 1. The 41/41 Master Reference Architecture

The canonical master reference is:
**`guides/best-noise-cancelling-headphones.html`**

All 41 existing articles have been audited and standardized to this exact specification. Every future article must strictly replicate this architecture.

---

## 2. Mandatory Image Requirements

| Requirement | Specification | Implementation Details |
| :--- | :--- | :--- |
| **Location** | `assets/images/articles/[slug].jpg` | Local, first-party file served from Cloudflare Pages. No external hotlinking. |
| **Dimensions** | Exactly `1200 × 800` pixels | 3:2 aspect ratio matching the Master Reference and modern social preview cards. |
| **Color Space** | 3-Channel sRGB (`3ch`) | Clean standard RGB; no CMYK or alpha channel. |
| **Encoding** | Progressive JPEG (`SOF2` / `0xC2`) | Multi-scan progressive encoding for fast edge rendering and optimal crawler parsing. |
| **Metadata** | **Zero ICC Profile (`0xE2`)**<br>**Zero EXIF Metadata (`0xE1`)** | All non-standard chunks stripped to eliminate social crawler decoding crashes. |
| **File Size** | Under 250 KB (typically 60–120 KB) | Optimized with `quality=85` and `optimize=True`. |
| **Cropping** | Subject-aware framing | Center or focal-point crop without stretching or distorting aspect ratio. |

---

## 3. Mandatory Social Metadata Tags (`<head>`)

Every article's `<head>` must include the exact Open Graph and Twitter Card tags in this precise sequence:

```html
  <!-- Open Graph / Social Meta -->
  <meta property="og:type" content="article">
  <meta property="og:title" content="[Article Title] | SmartGearPick">
  <meta property="og:description" content="[Concise Meta Description]">
  <meta property="og:url" content="https://smartgearpick.com/[section]/[slug]">
  <meta property="og:image" content="https://smartgearpick.com/assets/images/articles/[slug].jpg">
  <meta property="og:image:secure_url" content="https://smartgearpick.com/assets/images/articles/[slug].jpg">
  <meta property="og:image:type" content="image/jpeg">
  <meta property="og:image:width" content="1200">
  <meta property="og:image:height" content="800">

  <!-- Twitter Card Meta -->
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="[Article Title] | SmartGearPick">
  <meta name="twitter:description" content="[Concise Meta Description]">
  <meta name="twitter:image" content="https://smartgearpick.com/assets/images/articles/[slug].jpg">
```

---

## 4. Mandatory Hero Image in Article Body

```html
<div class="article-hero-image">
  <img src="/assets/images/articles/[slug].jpg" alt="[Descriptive Alt Text]" loading="eager" width="1200" height="800">
</div>
```

---

## 5. Automated Tooling & Commands

### Process a New Image
To process any input image (local file or web URL) into the compliant standard:
```bash
python scripts/process-article-image.py <source_path_or_url> <article-slug>
```

### Run Pre-Deployment Audit
To validate all articles against the master standard before pushing to `main`:
```bash
# Local audit (metadata + image binary verification):
node scripts/validate-articles.js

# Remote audit (also checks live HTTPS 200 responses):
node scripts/validate-articles.js --remote
```

---

## 6. Pre-Flight Checklist for New Articles

- [ ] Image processed via `scripts/process-article-image.py` into `assets/images/articles/[slug].jpg`.
- [ ] Image verified at 1200×800, Progressive JPEG, 0 ICC profile chunks, 0 EXIF chunks.
- [ ] `<head>` metadata block follows exact tag order with `summary_large_image`, `1200x800`, `image/jpeg`.
- [ ] Article body hero image references `/assets/images/articles/[slug].jpg` with `loading="eager"`.
- [ ] `node scripts/validate-articles.js` passes with 0 errors.
- [ ] Existing approved articles remain untouched.
