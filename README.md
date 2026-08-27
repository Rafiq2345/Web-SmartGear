# SmartGearPick.com — Static Architecture & Content Migration

SmartGearPick.com is built as a high-performance, modern, semantic static HTML/CSS/JavaScript publication.

---

## 📁 Project Architecture & Directory Structure

```text
Web-SmartGear/
├── content-audit.md           # 43-article inventory, testing claim audit rules, and classifications
├── migration-map.csv          # SEO URL migration map from Blogger to static routes
├── index.html                 # Homepage (Hero, Featured Reviews, Buying Guides, Affiliate Top Picks)
├── about.html                 # Editorial mission & transparent research methodology
├── contact.html               # Contact & correction inquiries
├── privacy-policy.html        # FTC affiliate disclosure & privacy policy
│
├── assets/
│   ├── css/
│   │   └── style.css          # Design system, CSS custom properties, responsive layout, dark theme
│   └── js/
│       └── main.js            # Mobile drawer, TOC scrollspy, Amazon affiliate tracking attribution
│
├── categories/                # Primary Category Hubs
│   ├── laptops.html
│   ├── smartphones.html
│   ├── audio.html
│   ├── gaming.html
│   ├── smart-home.html
│   └── accessories.html
│
├── guides/                    # Buying Guides & Educational Pillar Guides
│   ├── index.html             # Cross-category Buying Guides discovery hub
│   ├── best-laptops-under-1000.html
│   ├── best-laptops-for-students.html
│   ├── best-tablets-for-students.html
│   ├── best-laptop-stands.html
│   ├── best-power-banks.html
│   ├── best-mechanical-keyboards.html
│   └── back-to-school-checklist.html
│
├── reviews/                   # In-depth Hardware Reviews
│   └── apple-macbook-air-m5-review.html
│
├── comparisons/               # Head-to-Head Product Comparisons
│   └── sony-wf-1000xm6-vs-airpods-pro-3.html
│
└── hubs/                      # Dedicated SEO & Internal Linking Topic Hubs
    └── back-to-school-tech.html
```

---

## ⚡ Key Architectural Features

1. **Transparent Evaluation Standards**:
   - Strictly prohibits fabricated testing phrasing ("we lab-tested 15+ units for 30 days").
   - Grounded in manufacturer technical blueprints, USB-IF protocol standards, VESA certifications, and aggregate benchmark data (Geekbench 6, Cinebench 2024).
2. **Content-Type Badges**:
   - Single clean primary badge per card: `Review`, `Buying Guide`, `Comparison`, `Guide` alongside category tags.
3. **Modular Affiliate Attribution**:
   - Buttons use `data-product`, `data-location`, and `data-category`.
   - JavaScript manages tracking IDs without hardcoding fake live IDs:
     - `HOME_TRACKING_ID`
     - `REVIEW_TRACKING_ID`
     - `GUIDE_TRACKING_ID`
     - `COMPARISON_TRACKING_ID`
     - `CATEGORY_TRACKING_ID`
4. **AdSense Ready**:
   - Non-disruptive containers marked with `<!-- Future AdSense placement -->` post-intro, mid-content, and pre-conclusion.
5. **Back-to-School Topic Hub**:
   - Interlinks student laptops, tablets, chargers, laptop stands, and audio into an internal topic cluster.
6. **Zero Build Step Requirement**:
   - Fast, dependency-free static files ready for instant deployment to GitHub Pages, Cloudflare Pages, Netlify, or Vercel.