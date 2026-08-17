/* ============================================================
   BLOG CATEGORY FILTER
   ============================================================ */
(function () {
  const filterBtns  = document.querySelectorAll('.filter-btn');
  const blogCards   = document.querySelectorAll('#blogGrid .blog-card');
  const featuredPost = document.querySelector('.featured-post');

  filterBtns.forEach(function (btn) {
    btn.addEventListener('click', function () {
      // Update active button
      filterBtns.forEach(function (b) { b.classList.remove('active'); });
      btn.classList.add('active');

      var cat = btn.dataset.cat;

      // Filter featured post
      if (featuredPost) {
        if (cat === 'all' || featuredPost.dataset.cat === cat) {
          featuredPost.classList.remove('hidden');
        } else {
          featuredPost.classList.add('hidden');
        }
      }

      // Filter grid cards
      blogCards.forEach(function (card) {
        if (cat === 'all' || card.dataset.cat === cat) {
          card.classList.remove('hidden');
        } else {
          card.classList.add('hidden');
        }
      });
    });
  });
})();

/* ============================================================
   PAGINATION (static demo)
   ============================================================ */
(function () {
  var pageBtns = document.querySelectorAll('.page-btn:not(.page-btn--arrow)');
  pageBtns.forEach(function (btn) {
    btn.addEventListener('click', function () {
      pageBtns.forEach(function (b) { b.classList.remove('page-btn--active'); });
      btn.classList.add('page-btn--active');
      // Scroll to top of blog grid
      var grid = document.querySelector('.blog-main');
      if (grid) grid.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  });
})();

/* ============================================================
   NAVBAR HAMBURGER (same as main site)
   ============================================================ */
(function () {
  var hamburger = document.getElementById('hamburger');
  var navLinks  = document.querySelector('.nav-links');
  var navCta    = document.querySelector('.nav-cta');

  if (!hamburger) return;

  hamburger.addEventListener('click', function () {
    var isOpen = navLinks.classList.toggle('open');
    hamburger.setAttribute('aria-expanded', String(isOpen));
    if (navCta) navCta.style.display = isOpen ? 'inline-flex' : '';
  });

  document.addEventListener('click', function (e) {
    if (!hamburger.contains(e.target) && !navLinks.contains(e.target)) {
      navLinks.classList.remove('open');
    }
  });
})();

/* ============================================================
   STICKY NAVBAR SHADOW
   ============================================================ */
(function () {
  var navbar = document.querySelector('.navbar');
  if (!navbar) return;
  window.addEventListener('scroll', function () {
    navbar.style.boxShadow = window.scrollY > 10
      ? '0 4px 24px rgba(0,0,0,.10)'
      : '0 2px 12px rgba(0,0,0,.06)';
  });
})();
