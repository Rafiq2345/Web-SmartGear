# SmartGearPick — AI Agent Coding & Content Standards

All AI assistants and contributors modifying or creating content in this repository must strictly enforce the following production standards.

---

## 1. Master Reference Architecture

The canonical master reference for all social metadata and image delivery is:
**`guides/best-noise-cancelling-headphones.html`**

Every article in `guides/`, `reviews/`, `comparisons/`, and `hubs/` must replicate this exact implementation.

---

## 2. Article Image Production Standard (1200 × 800 px)

Every article must have a dedicated first-party image adhering to:

| Property | Required Value | Rationale |
| :--- | :--- | :--- |
| **Storage Location** | `assets/images/articles/[slug].jpg` | First-party Cloudflare hosting; zero third-party hotlinking. |
| **Dimensions** | Exactly `1200 × 800` pixels (3:2 aspect ratio) | Matches Master Reference; 100% supported by X `summary_large_image` and Open Graph. |
| **Color Space** | 3-Channel sRGB (`3ch`) | Universal browser and social crawler compatibility. |
| **JPEG Encoding** | Progressive JPEG (`SOF2` / `0xC2` marker) | Fast rendering, optimal compression, standard for X media ingest. |
| **Metadata Stripping** | **No ICC Profile** (`APP2` / `0xE2`)<br>**No EXIF metadata** (`APP1` / `0xE1`) | Prevents social crawler decoder failures caused by unhandled color profile chunks. |
| **File Size** | Optimized under 250 KB (typically 60–120 KB) | Instant edge loading and fast crawler ingestion. |
| **Composition** | Subject-aware center cropping; never stretch or distort | Ensures key hardware subject remains centered in large card previews. |

### Automated Image Processing Tool
Use the built-in script to process or re-encode article images:
```bash
python scripts/process-article-image.py <input_image_path_or_url> <slug>
```

---

## 3. Social Metadata & Head Specification

Every article's `<head>` must include the exact Open Graph and Twitter Card tags in the following order:

```html
  <!-- Open Graph / Social Meta -->
  <meta property="og:type" content="article">
  <meta property="og:title" content="[Exact Article Title] | SmartGearPick">
  <meta property="og:description" content="[Exact Meta Description]">
  <meta property="og:url" content="https://smartgearpick.com/[directory]/[slug]">
  <meta property="og:image" content="https://smartgearpick.com/assets/images/articles/[slug].jpg">
  <meta property="og:image:secure_url" content="https://smartgearpick.com/assets/images/articles/[slug].jpg">
  <meta property="og:image:type" content="image/jpeg">
  <meta property="og:image:width" content="1200">
  <meta property="og:image:height" content="800">

  <!-- Twitter Card Meta -->
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="[Exact Article Title] | SmartGearPick">
  <meta name="twitter:description" content="[Exact Meta Description]">
  <meta name="twitter:image" content="https://smartgearpick.com/assets/images/articles/[slug].jpg">
```

### Key Requirements:
1. `og:image` and `twitter:image` must be **identical absolute HTTPS URLs**.
2. `og:image:width` must be `1200` and `og:image:height` must be `800`.
3. `og:image:type` must be `image/jpeg`.
4. `twitter:card` must be `summary_large_image`.
5. Canonical URL must point to `https://smartgearpick.com/[directory]/[slug]` without `.html` extension.

---

## 4. Hero Image Specification in `<body>`

The hero image in the article body must point to the identical local first-party image:

```html
<div class="article-hero-image">
  <img src="/assets/images/articles/[slug].jpg" alt="[Descriptive alt text]" loading="eager" width="1200" height="800">
</div>
```

---

## 5. Pre-Deployment Validation Gate

Before committing or deploying any new article or modification, run the automated validator:

```bash
node scripts/validate-articles.js
```

All articles must pass (41/41 or N/N) with 0 errors before deployment to production.
