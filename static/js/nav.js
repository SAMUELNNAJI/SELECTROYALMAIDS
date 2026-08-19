/* ============================================================
   nav.js  –  Shared hamburger / mobile nav for all pages
   Include this on every page that does NOT already load script.js
   ============================================================ */
(function () {
  'use strict';

  // base.html already loads script.js. This guard makes nav.js safe on pages
  // that include it too, rather than registering a duplicate toggle handler.
  if (window.__selectRoyalMobileNavInitialized) return;
  window.__selectRoyalMobileNavInitialized = true;

  var hamburger = document.getElementById('hamburger');
  var navLinks  = document.querySelector('.nav-links');
  var navCta    = document.querySelector('.nav-cta');

  if (!hamburger || !navLinks) return;

  /* ── helpers ── */
  function openMenu() {
    navLinks.classList.add('open');
    hamburger.setAttribute('aria-expanded', 'true');
    hamburger.classList.add('is-open');
    document.body.style.overflow = 'hidden';
    hamburger.style.zIndex = '101';
    injectMobileCta();
  }

  function closeMenu() {
    navLinks.classList.remove('open');
    hamburger.setAttribute('aria-expanded', 'false');
    hamburger.classList.remove('is-open');
    document.body.style.overflow = '';
    hamburger.style.zIndex = '';
    removeMobileCta();
  }

  function isOpen() {
    return navLinks.classList.contains('open');
  }

  /* ── inject Login + Find a Maid buttons into the mobile overlay ── */
  function injectMobileCta() {
    if (navLinks.querySelector('.mobile-nav-cta')) return;

    var loginHref = 'login.html';
    var loginText = 'Login';
    var findHref  = 'find-a-maid.html';

    if (navCta) {
      var loginAnchor = navCta.querySelector('.nav-login');
      var findAnchor  = navCta.querySelector('.nav-find-btn');
      if (loginAnchor) {
        loginHref = loginAnchor.getAttribute('href');
        loginText = loginAnchor.textContent.trim();
      }
      if (findAnchor) findHref = findAnchor.getAttribute('href');
    }

    var li = document.createElement('li');
    li.innerHTML =
      '<div class="mobile-nav-cta">' +
        '<a href="' + loginHref + '" class="mobile-login-btn">' + loginText + '</a>' +
        '<a href="' + findHref  + '" class="btn btn-primary">' +
          '<i class="fa-solid fa-magnifying-glass"></i> FIND A MAID' +
        '</a>' +
      '</div>';
    navLinks.appendChild(li);
  }

  function removeMobileCta() {
    var existing = navLinks.querySelector('.mobile-nav-cta');
    if (existing && existing.parentElement) {
      existing.parentElement.remove();
    }
  }

  /* ── toggle ── */
  hamburger.addEventListener('click', function (e) {
    e.stopPropagation();
    isOpen() ? closeMenu() : openMenu();
  });

  /* ── close when any nav link is tapped ── */
  navLinks.addEventListener('click', function (e) {
    var target = e.target.closest('a');
    if (target) closeMenu();
  });

  /* ── close on outside click ── */
  document.addEventListener('click', function (e) {
    if (isOpen() && !hamburger.contains(e.target) && !navLinks.contains(e.target)) {
      closeMenu();
    }
  });

  /* ── close on Escape ── */
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && isOpen()) closeMenu();
  });

  /* ── close on resize back to desktop ── */
  window.addEventListener('resize', function () {
    if (window.innerWidth > 900 && isOpen()) closeMenu();
  });

  /* ── Sticky navbar shadow on scroll ── */
  var navbar = document.querySelector('.navbar');
  if (navbar) {
    window.addEventListener('scroll', function () {
      navbar.style.boxShadow = window.scrollY > 10
        ? '0 4px 24px rgba(0,0,0,.10)'
        : '0 2px 12px rgba(0,0,0,.06)';
    });
  }
})();
