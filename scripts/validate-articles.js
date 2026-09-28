#!/usr/bin/env node
/**
 * SmartGearPick — Article & Social Image Pre-Deployment Validator
 * Audits all articles against the Master Reference specification.
 *
 * Usage:
 *   node scripts/validate-articles.js
 *   node scripts/validate-articles.js --remote  (also verifies live HTTPS 200)
 */

const fs = require('fs');
const path = require('path');
const https = require('https');

const REPO_ROOT = path.resolve(__dirname, '..');
const ARTICLE_DIRS = ['guides', 'reviews', 'comparisons', 'hubs'];

function parseJpeg(buf) {
  if (buf.length < 4 || buf[0] !== 0xFF || buf[1] !== 0xD8) {
    return { valid: false, error: 'Missing SOI marker (FF D8)' };
  }
  let offset = 2;
  let isProgressive = false;
  let width = 0, height = 0, channels = 0;
  let hasICC = false, hasEXIF = false;

  while (offset < buf.length - 1) {
    if (buf[offset] === 0xFF) {
      const m = buf[offset + 1];
      if (m === 0xD9 || m === 0xDA) break; // EOI or SOS
      if (m >= 0xC0 && m <= 0xCF && m !== 0xC4 && m !== 0xC8 && m !== 0xCC) {
        const len = buf.readUInt16BE(offset + 2);
        height = buf.readUInt16BE(offset + 5);
        width = buf.readUInt16BE(offset + 7);
        channels = buf[offset + 9];
        if (m === 0xC2) isProgressive = true;
        offset += 2 + len;
        continue;
      }
      if (m === 0xE1) {
        const len = buf.readUInt16BE(offset + 2);
        const str = buf.slice(offset + 4, offset + 4 + 4).toString('ascii');
        if (str.startsWith('Exif')) hasEXIF = true;
        offset += 2 + len;
        continue;
      }
      if (m === 0xE2) {
        const len = buf.readUInt16BE(offset + 2);
        const str = buf.slice(offset + 4, offset + 4 + 11).toString('ascii');
        if (str.startsWith('ICC_PROFILE')) hasICC = true;
        offset += 2 + len;
        continue;
      }
      if ((m >= 0xE0 && m <= 0xEF) || m === 0xDB || m === 0xC4) {
        const len = buf.readUInt16BE(offset + 2);
        offset += 2 + len;
        continue;
      }
    }
    offset++;
  }

  return {
    valid: true,
    width,
    height,
    channels,
    isProgressive,
    hasICC,
    hasEXIF,
    sizeBytes: buf.length
  };
}

function checkUrl(url) {
  return new Promise((resolve) => {
    https.get(url, { headers: { 'User-Agent': 'Twitterbot/1.0' } }, (res) => {
      resolve({ statusCode: res.statusCode, contentType: res.headers['content-type'] });
    }).on('error', (e) => resolve({ statusCode: 0, error: e.message }));
  });
}

async function run() {
  const isRemote = process.argv.includes('--remote');
  console.log('\n===============================================================');
  console.log(' SMARTGEARPICK ARTICLE & SOCIAL IMAGE VALIDATION AUDIT');
  console.log(` Mode: Local Image & Metadata Audit${isRemote ? ' + Remote HTTPS 200 Verification' : ''}`);
  console.log('===============================================================\n');

  const articleFiles = [];
  for (const dir of ARTICLE_DIRS) {
    const fullDir = path.join(REPO_ROOT, dir);
    if (!fs.existsSync(fullDir)) continue;
    const files = fs.readdirSync(fullDir).filter(f => f.endsWith('.html') && f !== 'index.html');
    for (const f of files) {
      articleFiles.push({ section: dir, file: f, fullPath: path.join(fullDir, f) });
    }
  }

  console.log(`Discovered ${articleFiles.length} article pages across ${ARTICLE_DIRS.join(', ')}.\n`);

  let passedCount = 0;
  let failedCount = 0;
  const failures = [];

  for (const item of articleFiles) {
    const slug = item.file.replace('.html', '');
    const html = fs.readFileSync(item.fullPath, 'utf-8');
    const errors = [];

    // 1. Social metadata validation
    const ogType = (html.match(/<meta\s+property=["']og:type["']\s+content=["']([^"']+)["']/i) || [])[1];
    const ogTitle = (html.match(/<meta\s+property=["']og:title["']\s+content=["']([^"']+)["']/i) || [])[1];
    const ogDesc = (html.match(/<meta\s+property=["']og:description["']\s+content=["']([^"']+)["']/i) || [])[1];
    const ogUrl = (html.match(/<meta\s+property=["']og:url["']\s+content=["']([^"']+)["']/i) || [])[1];
    const ogImg = (html.match(/<meta\s+property=["']og:image["']\s+content=["']([^"']+)["']/i) || [])[1];
    const ogSecureImg = (html.match(/<meta\s+property=["']og:image:secure_url["']\s+content=["']([^"']+)["']/i) || [])[1];
    const ogTypeImg = (html.match(/<meta\s+property=["']og:image:type["']\s+content=["']([^"']+)["']/i) || [])[1];
    const ogW = (html.match(/<meta\s+property=["']og:image:width["']\s+content=["']([^"']+)["']/i) || [])[1];
    const ogH = (html.match(/<meta\s+property=["']og:image:height["']\s+content=["']([^"']+)["']/i) || [])[1];

    const twCard = (html.match(/<meta\s+name=["']twitter:card["']\s+content=["']([^"']+)["']/i) || [])[1];
    const twTitle = (html.match(/<meta\s+name=["']twitter:title["']\s+content=["']([^"']+)["']/i) || [])[1];
    const twDesc = (html.match(/<meta\s+name=["']twitter:description["']\s+content=["']([^"']+)["']/i) || [])[1];
    const twImg = (html.match(/<meta\s+name=["']twitter:image["']\s+content=["']([^"']+)["']/i) || [])[1];

    if (ogType !== 'article') errors.push(`og:type is "${ogType}" (expected "article")`);
    if (!ogTitle) errors.push('Missing og:title');
    if (!ogDesc) errors.push('Missing og:description');
    if (!ogUrl || !ogUrl.startsWith('https://smartgearpick.com/')) errors.push(`og:url invalid: ${ogUrl}`);
    if (!ogImg || !ogImg.endsWith('.jpg')) errors.push(`og:image invalid: ${ogImg}`);
    if (ogSecureImg !== ogImg) errors.push('og:image:secure_url does not match og:image');
    if (ogTypeImg !== 'image/jpeg') errors.push(`og:image:type is "${ogTypeImg}" (expected "image/jpeg")`);
    if (ogW !== '1200') errors.push(`og:image:width is "${ogW}" (expected "1200")`);
    if (ogH !== '800') errors.push(`og:image:height is "${ogH}" (expected "800")`);

    if (twCard !== 'summary_large_image') errors.push(`twitter:card is "${twCard}" (expected "summary_large_image")`);
    if (twTitle !== ogTitle) errors.push('twitter:title does not match og:title');
    if (twDesc !== ogDesc) errors.push('twitter:description does not match og:description');
    if (twImg !== ogImg) errors.push('twitter:image does not match og:image');

    // 2. Image File Binary Verification
    const expectedImgPath = path.join(REPO_ROOT, 'assets', 'images', 'articles', `${slug}.jpg`);
    if (!fs.existsSync(expectedImgPath)) {
      errors.push(`Local image file missing: assets/images/articles/${slug}.jpg`);
    } else {
      const imgBuf = fs.readFileSync(expectedImgPath);
      const jpeg = parseJpeg(imgBuf);
      if (!jpeg.valid) {
        errors.push(`Image parse error: ${jpeg.error}`);
      } else {
        if (jpeg.width !== 1200 || jpeg.height !== 800) {
          errors.push(`Image dimensions ${jpeg.width}x${jpeg.height} (expected 1200x800)`);
        }
        if (jpeg.channels !== 3) {
          errors.push(`Image channels ${jpeg.channels} (expected 3 RGB)`);
        }
        if (!jpeg.isProgressive) {
          errors.push('Image is not Progressive JPEG (missing SOF2 0xC2)');
        }
        if (jpeg.hasICC) {
          errors.push('Image contains embedded ICC profile (APP2 chunk present)');
        }
        if (jpeg.hasEXIF) {
          errors.push('Image contains embedded EXIF metadata (APP1 chunk present)');
        }
        if (jpeg.sizeBytes > 250 * 1024) {
          errors.push(`Image file size ${jpeg.sizeBytes} bytes exceeds 250 KB limit`);
        }
      }
    }

    // 3. Hero image in HTML body check
    const heroMatch = html.match(/<img[^>]+src=["'](\/assets\/images\/articles\/[^"']+)["'][^>]*>/i);
    if (!heroMatch) {
      errors.push('Article body missing first-party hero image tag (/assets/images/articles/...)');
    }

    // 4. Remote live HTTP 200 check if requested
    if (isRemote && errors.length === 0) {
      const pageRes = await checkUrl(`https://smartgearpick.com/${item.section}/${slug}`);
      if (pageRes.statusCode !== 200) errors.push(`Remote page HTTP status: ${pageRes.statusCode}`);
      const imgRes = await checkUrl(`https://smartgearpick.com/assets/images/articles/${slug}.jpg`);
      if (imgRes.statusCode !== 200) errors.push(`Remote image HTTP status: ${imgRes.statusCode}`);
    }

    if (errors.length === 0) {
      passedCount++;
      console.log(` [PASS] ${item.section}/${item.file} -> assets/images/articles/${slug}.jpg`);
    } else {
      failedCount++;
      console.log(` [FAIL] ${item.section}/${item.file}`);
      errors.forEach(e => console.log(`        - ${e}`));
      failures.push({ file: `${item.section}/${item.file}`, errors });
    }
  }

  console.log('\n===============================================================');
  console.log(` AUDIT SUMMARY: ${passedCount}/${articleFiles.length} PASSED (${failedCount} FAILED)`);
  console.log('===============================================================\n');

  if (failedCount > 0) {
    process.exit(1);
  } else {
    console.log(' All articles strictly comply with the Master Reference Standard.\n');
  }
}

run();
