/* ============================================================
   HERO CAROUSEL
   ============================================================ */
(function () {
  const slides  = document.querySelectorAll('.hero-slide');
  const dots    = document.querySelectorAll('#heroDots .dot');
  const prevBtn = document.getElementById('heroPrev');
  const nextBtn = document.getElementById('heroNext');

  if (!slides.length || !prevBtn || !nextBtn) return;

  let current = 0;
  let timer   = null;

  function showSlide(index) {
    // Wrap around
    const next = (index + slides.length) % slides.length;

    // Remove active from current
    slides[current].classList.remove('active');
    if (dots[current]) dots[current].classList.remove('active');

    // Set new current
    current = next;
    slides[current].classList.add('active');
    if (dots[current]) dots[current].classList.add('active');
  }

  function startAutoPlay() {
    stopAutoPlay();
    timer = setInterval(function () {
      showSlide(current + 1);
    }, 10000);
  }

  function stopAutoPlay() {
    if (timer) {
      clearInterval(timer);
      timer = null;
    }
  }

  // Arrow buttons
  prevBtn.addEventListener('click', function () {
    showSlide(current - 1);
    startAutoPlay();
  });

  nextBtn.addEventListener('click', function () {
    showSlide(current + 1);
    startAutoPlay();
  });

  // Dot buttons
  dots.forEach(function (dot) {
    dot.addEventListener('click', function () {
      showSlide(parseInt(this.dataset.index, 10));
      startAutoPlay();
    });
  });

  // Pause on hover
  var carousel = document.querySelector('.hero-carousel');
  if (carousel) {
    carousel.addEventListener('mouseenter', stopAutoPlay);
    carousel.addEventListener('mouseleave', startAutoPlay);
  }

  // Kick off
  startAutoPlay();
})();

/* ============================================================
   ANIMATED STAT COUNTERS
   ============================================================ */
(function () {
  const counters = document.querySelectorAll('.stat-number');

  function animateCounter(el) {
    const target   = parseInt(el.dataset.target, 10);
    const duration = 2000;
    const step     = target / (duration / 16);
    let val        = 0;

    function tick() {
      val = Math.min(val + step, target);
      el.textContent = Math.floor(val).toLocaleString();
      if (val < target) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
  }

  const observer = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (entry.isIntersecting) {
        animateCounter(entry.target);
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.5 });

  counters.forEach(function (c) { observer.observe(c); });
})();

/* ============================================================
   NAVBAR MOBILE HAMBURGER
   ============================================================ */
(function () {
  const hamburger = document.getElementById('hamburger');
  const navLinks  = document.querySelector('.nav-links');
  const navCta    = document.querySelector('.nav-cta');

  if (!hamburger) return;

  hamburger.addEventListener('click', function () {
    const isOpen = navLinks.classList.toggle('open');
    hamburger.setAttribute('aria-expanded', String(isOpen));
    hamburger.classList.toggle('is-open', isOpen);
    // Lock body scroll and keep hamburger on top of overlay
    document.body.style.overflow = isOpen ? 'hidden' : '';
    hamburger.style.zIndex = isOpen ? '100' : '';
    if (navCta) navCta.style.display = isOpen ? 'inline-flex' : '';
  });

  document.addEventListener('click', function (e) {
    if (!hamburger.contains(e.target) && !navLinks.contains(e.target)) {
      navLinks.classList.remove('open');
      hamburger.setAttribute('aria-expanded', 'false');
      hamburger.classList.remove('is-open');
      document.body.style.overflow = '';
      hamburger.style.zIndex = '';
    }
  });
})();

/* ============================================================
   STICKY NAVBAR SHADOW ON SCROLL
   ============================================================ */
(function () {
  const navbar = document.querySelector('.navbar');
  if (!navbar) return;
  window.addEventListener('scroll', function () {
    navbar.style.boxShadow = window.scrollY > 10
      ? '0 4px 24px rgba(0,0,0,.10)'
      : '0 2px 12px rgba(0,0,0,.06)';
  });
})();

/* ============================================================
   SCROLL REVEAL (lightweight)
   ============================================================ */
(function () {
  const revealEls = document.querySelectorAll(
    '.service-card, .step-card-v2, .maid-card, .stat-card, .testi-featured-card, .mini-review'
  );

  const style = document.createElement('style');
  style.textContent = [
    '.reveal { opacity: 0; transform: translateY(24px);',
    '  transition: opacity .5s ease, transform .5s ease; }',
    '.reveal.visible { opacity: 1; transform: translateY(0); }'
  ].join(' ');
  document.head.appendChild(style);

  revealEls.forEach(function (el, i) {
    el.classList.add('reveal');
    el.style.transitionDelay = ((i % 4) * 80) + 'ms';
  });

  const observer = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.15 });

  revealEls.forEach(function (el) { observer.observe(el); });
})();

/* ============================================================
   TESTIMONIALS CAROUSEL
   ============================================================ */
(function () {
  const slides  = document.querySelectorAll('.testi-slide');
  const tdots   = document.querySelectorAll('#testiDots .tdot');
  const prevBtn = document.getElementById('testiPrev');
  const nextBtn = document.getElementById('testiNext');

  if (!slides.length || !prevBtn || !nextBtn) return;

  let current = 0;
  let timer   = null;

  // Init
  slides.forEach(function (s, i) { s.classList.toggle('active', i === 0); });
  tdots.forEach(function (d, i)  { d.classList.toggle('active', i === 0); });

  function showSlide(index) {
    const next = (index + slides.length) % slides.length;
    slides[current].classList.remove('active');
    if (tdots[current]) tdots[current].classList.remove('active');
    current = next;
    slides[current].classList.add('active');
    if (tdots[current]) tdots[current].classList.add('active');
  }

  function startAutoPlay() {
    stopAutoPlay();
    timer = setInterval(function () { showSlide(current + 1); }, 6000);
  }

  function stopAutoPlay() {
    if (timer) { clearInterval(timer); timer = null; }
  }

  prevBtn.addEventListener('click', function () { showSlide(current - 1); startAutoPlay(); });
  nextBtn.addEventListener('click', function () { showSlide(current + 1); startAutoPlay(); });

  tdots.forEach(function (dot) {
    dot.addEventListener('click', function () {
      showSlide(parseInt(this.dataset.index, 10));
      startAutoPlay();
    });
  });

  var tc = document.querySelector('.testi-carousel');
  if (tc) {
    tc.addEventListener('mouseenter', stopAutoPlay);
    tc.addEventListener('mouseleave', startAutoPlay);
  }

  startAutoPlay();
})();
