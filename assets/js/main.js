/**
 * SmartGearPick.com - Core Interactive Scripts
 * Architecture: Static Vanilla JS
 */

document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  initMobileNav();
  initSearchModal();
  initTableOfContents();
  initAffiliateTracking();
  initFaqAccordion();
  initArticleFilter();
});

/* --------------------------------------------------------------------------
   1. Theme Switcher (Light / Dark Mode with Persistence)
   -------------------------------------------------------------------------- */
function initTheme() {
  const themeToggleBtn = document.getElementById('theme-toggle-btn');
  const storedTheme = localStorage.getItem('sgp_theme');
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  
  const currentTheme = storedTheme || (prefersDark ? 'dark' : 'light');
  document.documentElement.setAttribute('data-theme', currentTheme);
  updateThemeIcon(currentTheme);

  if (themeToggleBtn) {
    themeToggleBtn.addEventListener('click', () => {
      const activeTheme = document.documentElement.getAttribute('data-theme');
      const newTheme = activeTheme === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', newTheme);
      localStorage.setItem('sgp_theme', newTheme);
      updateThemeIcon(newTheme);
    });
  }
}

function updateThemeIcon(theme) {
  const themeIcon = document.getElementById('theme-icon');
  if (themeIcon) {
    themeIcon.textContent = theme === 'dark' ? '☀️' : '🌙';
  }
}

/* --------------------------------------------------------------------------
   2. Mobile Navigation Drawer
   -------------------------------------------------------------------------- */
function initMobileNav() {
  const mobileToggle = document.getElementById('mobile-menu-toggle');
  const mobileDrawer = document.getElementById('mobile-nav-drawer');

  if (mobileToggle && mobileDrawer) {
    mobileToggle.addEventListener('click', () => {
      const isOpen = mobileDrawer.classList.toggle('is-open');
      mobileToggle.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
      mobileToggle.innerHTML = isOpen ? '✕' : '☰';
    });

    // Close on navigation link click
    mobileDrawer.querySelectorAll('a').forEach(link => {
      link.addEventListener('click', () => {
        mobileDrawer.classList.remove('is-open');
        mobileToggle.setAttribute('aria-expanded', 'false');
        mobileToggle.innerHTML = '☰';
      });
    });
  }
}

/* --------------------------------------------------------------------------
   3. Global Search Modal
   -------------------------------------------------------------------------- */
function initSearchModal() {
  const searchBtn = document.getElementById('search-toggle-btn');
  const searchModal = document.getElementById('search-modal');
  const searchClose = document.getElementById('search-modal-close');
  const searchInput = document.getElementById('site-global-search');
  const resultsContainer = document.getElementById('search-results-container');

  if (!searchBtn || !searchModal) return;

  const openModal = () => {
    searchModal.classList.add('is-active');
    searchModal.setAttribute('aria-hidden', 'false');
    if (searchInput) {
      setTimeout(() => searchInput.focus(), 50);
    }
  };

  const closeModal = () => {
    searchModal.classList.remove('is-active');
    searchModal.setAttribute('aria-hidden', 'true');
  };

  searchBtn.addEventListener('click', openModal);

  if (searchClose) {
    searchClose.addEventListener('click', closeModal);
  }

  searchModal.addEventListener('click', (e) => {
    if (e.target === searchModal) {
      closeModal();
    }
  });

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && searchModal.classList.contains('is-active')) {
      closeModal();
    }
  });

  // Client-side quick filter across search modal
  if (searchInput && resultsContainer) {
    const isSubdir = window.location.pathname.includes('/categories/') || 
                     window.location.pathname.includes('/guides/') || 
                     window.location.pathname.includes('/reviews/') || 
                     window.location.pathname.includes('/comparisons/') || 
                     window.location.pathname.includes('/hubs/');
    const pathPrefix = isSubdir ? '../' : '';

    const siteLinks = [
      { title: 'Apple MacBook Air M5 Review', url: 'reviews/apple-macbook-air-m5-review.html', cat: 'Reviews • Laptops' },
      { title: 'Best Laptops Under $1,000 in 2026', url: 'guides/best-laptops-under-1000.html', cat: 'Buying Guides • Laptops' },
      { title: 'Best Laptops for Students 2026', url: 'guides/best-laptops-for-students.html', cat: 'Buying Guides • Laptops' },
      { title: 'Sony WF-1000XM6 vs AirPods Pro 3', url: 'comparisons/sony-wf-1000xm6-vs-airpods-pro-3.html', cat: 'Comparisons • Audio' },
      { title: 'Best Mechanical Keyboards 2026', url: 'guides/best-mechanical-keyboards.html', cat: 'Buying Guides • Gaming' },
      { title: 'Best Tablets for Students 2026', url: 'guides/best-tablets-for-students.html', cat: 'Buying Guides • Mobile' },
      { title: 'Best Laptop Stands 2026', url: 'guides/best-laptop-stands.html', cat: 'Buying Guides • Accessories' },
      { title: 'Best Power Banks 2026', url: 'guides/best-power-banks.html', cat: 'Buying Guides • Accessories' },
      { title: 'Back-to-School Tech Checklist 2026', url: 'guides/back-to-school-checklist.html', cat: 'Hub • Back-to-School Tech' },
      { title: 'All Buying Guides Hub', url: 'guides/index.html', cat: 'Hub • Guides' },
      { title: 'All Tech Reviews Hub', url: 'reviews/index.html', cat: 'Hub • Reviews' },
      { title: 'Head-to-Head Comparisons Hub', url: 'comparisons/index.html', cat: 'Hub • Comparisons' }
    ];

    searchInput.addEventListener('input', (e) => {
      const term = e.target.value.toLowerCase().trim();
      if (!term) {
        resultsContainer.innerHTML = '<p style="margin: 0; color: var(--text-muted);">Type keywords to filter topics across SmartGearPick.</p>';
        return;
      }

      const filtered = siteLinks.filter(item => 
        item.title.toLowerCase().includes(term) || item.cat.toLowerCase().includes(term)
      );

      if (filtered.length === 0) {
        resultsContainer.innerHTML = `<p style="margin: 0; color: var(--text-muted);">No matching guides found for "<strong>${escapeHtml(term)}</strong>".</p>`;
      } else {
        resultsContainer.innerHTML = filtered.map(item => `
          <div style="padding: 0.6rem 0; border-bottom: 1px solid var(--border-light);">
            <a href="${pathPrefix}${item.url}" style="font-weight: 700; color: var(--text-primary); display: block; line-height: 1.35;">${escapeHtml(item.title)}</a>
            <span style="font-size: 0.75rem; color: var(--text-muted);">${escapeHtml(item.cat)}</span>
          </div>
        `).join('');
      }
    });
  }
}

function escapeHtml(str) {
  return str.replace(/[&<>'"]/g, 
    tag => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[tag] || tag)
  );
}

/* --------------------------------------------------------------------------
   4. Table of Contents Scrollspy
   -------------------------------------------------------------------------- */
function initTableOfContents() {
  const tocLinks = document.querySelectorAll('.toc-link');
  const headings = document.querySelectorAll('.article-prose h2, .article-prose h3');

  if (tocLinks.length === 0 || headings.length === 0) return;

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          const id = entry.target.getAttribute('id');
          if (id) {
            tocLinks.forEach((link) => {
              if (link.getAttribute('href') === `#${id}`) {
                link.classList.add('active');
              } else {
                link.classList.remove('active');
              }
            });
          }
        }
      });
    },
    {
      rootMargin: '-80px 0px -60% 0px',
      threshold: 0
    }
  );

  headings.forEach((heading) => {
    if (heading.id) {
      observer.observe(heading);
    }
  });
}

/* --------------------------------------------------------------------------
   5. Amazon Affiliate Tracking Tag Strategy & Attribution
   -------------------------------------------------------------------------- */
const AFFILIATE_TRACKING_CONFIG = {
  homepage: 'HOME_TRACKING_ID',
  article: 'REVIEW_TRACKING_ID',
  guide: 'GUIDE_TRACKING_ID',
  comparison: 'COMPARISON_TRACKING_ID',
  category: 'CATEGORY_TRACKING_ID',
  default: 'DEFAULT_TRACKING_ID'
};

function initAffiliateTracking() {
  const affiliateButtons = document.querySelectorAll('[data-product]');

  affiliateButtons.forEach((btn) => {
    btn.addEventListener('click', (e) => {
      const product = btn.getAttribute('data-product') || 'unknown';
      const location = btn.getAttribute('data-location') || 'default';
      const category = btn.getAttribute('data-category') || 'general';
      const trackingTag = AFFILIATE_TRACKING_CONFIG[location] || AFFILIATE_TRACKING_CONFIG.default;

      // Construct destination Amazon URL with tracking parameters if placeholder is active
      const currentHref = btn.getAttribute('href');
      if (currentHref && currentHref.startsWith('https://www.amazon.com')) {
        try {
          const url = new URL(currentHref);
          // Only append tag if tracking tag is configured
          if (trackingTag && !trackingTag.includes('TRACKING_ID')) {
            url.searchParams.set('tag', trackingTag);
            btn.setAttribute('href', url.toString());
          }
        } catch (err) {
          console.warn('Affiliate URL parsing error:', err);
        }
      }

      // Outbound affiliate click event telemetry
      if (window.gtag) {
        window.gtag('event', 'affiliate_click', {
          product_name: product,
          click_location: location,
          product_category: category,
          tracking_tag: trackingTag
        });
      }
    });
  });
}

/* --------------------------------------------------------------------------
   6. FAQ Accordion
   -------------------------------------------------------------------------- */
function initFaqAccordion() {
  const faqButtons = document.querySelectorAll('.faq-question');

  faqButtons.forEach((btn) => {
    btn.addEventListener('click', () => {
      const answer = btn.nextElementSibling;
      const isOpen = answer.style.display === 'block';

      // Close other accordions in the same group
      btn.closest('.faq-section')?.querySelectorAll('.faq-answer').forEach(el => {
        el.style.display = 'none';
      });
      btn.closest('.faq-section')?.querySelectorAll('.faq-question').forEach(el => {
        el.setAttribute('aria-expanded', 'false');
      });

      if (!isOpen) {
        answer.style.display = 'block';
        btn.setAttribute('aria-expanded', 'true');
      }
    });
  });
}

/* --------------------------------------------------------------------------
   7. Simple Search & Filter for Article Listings
   -------------------------------------------------------------------------- */
function initArticleFilter() {
  const searchInput = document.getElementById('site-article-search');
  const articleCards = document.querySelectorAll('.article-card, .mini-card');

  if (!searchInput || articleCards.length === 0) return;

  searchInput.addEventListener('input', (e) => {
    const term = e.target.value.toLowerCase().trim();

    articleCards.forEach((card) => {
      const title = card.querySelector('.card-title, .mini-card-title')?.textContent.toLowerCase() || '';
      const excerpt = card.querySelector('.card-excerpt')?.textContent.toLowerCase() || '';
      const category = card.querySelector('.badge-category')?.textContent.toLowerCase() || '';

      if (title.includes(term) || excerpt.includes(term) || category.includes(term)) {
        card.style.display = '';
      } else {
        card.style.display = 'none';
      }
    });
  });
}
