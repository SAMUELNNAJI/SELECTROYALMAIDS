/* ============================================================
   ANIMATIONS.JS — SelectRoyal Maids
   Scroll-reveal (Intersection Observer) + hero orbs + countUp
   ============================================================ */

(function () {
  'use strict';

  /* ── 1. Scroll-reveal ── */
  function initScrollReveal() {
    const els = document.querySelectorAll('[data-reveal]');
    if (!els.length) return;

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('is-visible');
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.12, rootMargin: '0px 0px -48px 0px' }
    );

    els.forEach((el) => observer.observe(el));
  }

  /* ── 2. Auto-stagger children inside [data-stagger] ── */
  function initStagger() {
    const groups = document.querySelectorAll('[data-stagger]');
    groups.forEach((group) => {
      const baseDelay = parseInt(group.dataset.stagger, 10) || 100;
      const children = group.querySelectorAll(':scope > *');
      children.forEach((child, i) => {
        if (!child.hasAttribute('data-reveal')) {
          child.setAttribute('data-reveal', 'up');
        }
        if (!child.hasAttribute('data-delay')) {
          child.setAttribute('data-delay', String(i * baseDelay));
        }
      });
    });
  }

  /* ── 3. Count-up numbers ── */
  function initCountUp() {
    const counters = document.querySelectorAll('[data-count]');
    if (!counters.length) return;

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          const el = entry.target;
          const target = parseFloat(el.dataset.count);
          const suffix = el.dataset.countSuffix || '';
          const prefix = el.dataset.countPrefix || '';
          const duration = 1600;
          const isDecimal = target % 1 !== 0;
          const start = performance.now();

          function tick(now) {
            const elapsed = now - start;
            const progress = Math.min(elapsed / duration, 1);
            // Ease-out quad
            const eased = 1 - (1 - progress) * (1 - progress);
            const current = target * eased;
            el.textContent = prefix + (isDecimal ? current.toFixed(1) : Math.floor(current)) + suffix;
            if (progress < 1) requestAnimationFrame(tick);
          }

          requestAnimationFrame(tick);
          observer.unobserve(el);
        });
      },
      { threshold: 0.5 }
    );

    counters.forEach((el) => observer.observe(el));
  }

  /* ── 4. Inject decorative orbs into dark hero sections ── */
  function initHeroOrbs() {
    const heroSelectors = [
      '.page-hero',
      '.post-hero',
      '.srv-hero',
      '.hiw-hero',
    ];
    heroSelectors.forEach((sel) => {
      const hero = document.querySelector(sel);
      if (!hero) return;
      // Avoid double-injecting
      if (hero.querySelector('.hero-orb')) return;
      [1, 2, 3].forEach((n) => {
        const orb = document.createElement('div');
        orb.className = `hero-orb hero-orb--${n}`;
        hero.appendChild(orb);
      });
    });
  }

  /* ── 5. Navbar shrink on scroll ── */
  function initNavbarScroll() {
    const navbar = document.querySelector('.navbar');
    if (!navbar) return;
    const onScroll = () => {
      navbar.classList.toggle('scrolled', window.scrollY > 20);
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
  }

  /* ── 6. Smooth active TOC link (blog post) ── */
  function initTOC() {
    const toc = document.querySelector('.post-toc');
    if (!toc) return;
    const headings = Array.from(document.querySelectorAll('.post-h2'));
    const links    = Array.from(toc.querySelectorAll('a'));
    if (!headings.length || !links.length) return;

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          const idx = headings.indexOf(entry.target);
          if (idx < 0) return;
          links.forEach((l) => l.classList.remove('active'));
          if (links[idx]) links[idx].classList.add('active');
        });
      },
      { threshold: 0.6 }
    );
    headings.forEach((h) => observer.observe(h));
  }

  /* ── INIT ── */
  function init() {
    initStagger();     // must run before initScrollReveal
    initScrollReveal();
    initCountUp();
    initHeroOrbs();
    initNavbarScroll();
    initTOC();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
