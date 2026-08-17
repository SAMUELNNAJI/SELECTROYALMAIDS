/* ============================================================
   FIND A MAID PAGE — find-a-maid.js
   ============================================================ */
(function () {
  'use strict';

  /* ---- DOM refs ---- */
  const grid          = document.getElementById('maidGrid');
  const cards         = Array.from(document.querySelectorAll('.fam-card'));
  const resultsCount  = document.getElementById('resultsCount');
  const noResults     = document.getElementById('noResults');
  const sortSelect    = document.getElementById('sortSelect');
  const clearAllBtn   = document.getElementById('clearAllFilters');
  const clearFromEmpty = document.getElementById('clearFromEmpty');
  const activeTagsEl  = document.getElementById('activeFilterTags');
  const filterBadge   = document.getElementById('filterBadge');
  const pageNumbers   = document.getElementById('pageNumbers');
  const prevPage      = document.getElementById('prevPage');
  const nextPage      = document.getElementById('nextPage');

  /* View toggle */
  const viewGrid = document.getElementById('viewGrid');
  const viewList = document.getElementById('viewList');

  /* Mobile sidebar */
  const sidebar       = document.getElementById('filterSidebar');
  const mobileBtn     = document.getElementById('mobileFilterToggle');
  const backdrop      = document.getElementById('sidebarBackdrop');
  const applyBtn      = document.getElementById('applyFiltersBtn');

  /* Hero search */
  const heroCity      = document.getElementById('heroCity');
  const heroRole      = document.getElementById('heroRole');
  const heroSearch    = document.getElementById('heroSearch');
  const heroSearchBtn = document.getElementById('heroSearchBtn');

  /* Skill tags */
  const skillTagBtns  = document.querySelectorAll('.fam-skill-tag');

  /* ---- State ---- */
  const CARDS_PER_PAGE = 9;
  let currentPage = 1;
  let filteredCards = [...cards];
  let activeSkills = new Set();
  let heroSearchQuery = '';

  /* ---- Collapse / expand filter groups ---- */
  document.querySelectorAll('.fam-filter-group-toggle').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var expanded = this.getAttribute('aria-expanded') === 'true';
      var bodyId   = this.getAttribute('aria-controls');
      var body     = document.getElementById(bodyId);
      this.setAttribute('aria-expanded', String(!expanded));
      if (body) body.classList.toggle('fam-filter-group-body--collapsed', expanded);
    });
  });

  /* ---- Skill tag toggles ---- */
  skillTagBtns.forEach(function (btn) {
    btn.addEventListener('click', function () {
      var skill = this.dataset.skill;
      if (activeSkills.has(skill)) {
        activeSkills.delete(skill);
        this.classList.remove('active');
      } else {
        activeSkills.add(skill);
        this.classList.add('active');
      }
      applyFilters();
    });
  });

  /* ---- Hero search ---- */
  function syncHeroToSidebar () {
    if (heroCity && heroCity.value) {
      var cb = document.querySelector('input[name="city"][value="' + heroCity.value + '"]');
      if (cb) cb.checked = true;
    }
    if (heroRole && heroRole.value) {
      var rb = document.querySelector('input[name="role"][value="' + heroRole.value + '"]');
      if (rb) rb.checked = true;
    }
    heroSearchQuery = heroSearch ? heroSearch.value.trim().toLowerCase() : '';
  }

  if (heroSearchBtn) {
    heroSearchBtn.addEventListener('click', function () {
      syncHeroToSidebar();
      applyFilters();
      document.querySelector('.fam-main-section').scrollIntoView({ behavior: 'smooth' });
    });
  }
  if (heroSearch) {
    heroSearch.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') heroSearchBtn.click();
    });
  }

  /* ---- Collect active filters from sidebar ---- */
  function getFilters () {
    return {
      cities:       Array.from(document.querySelectorAll('input[name="city"]:checked')).map(function (c) { return c.value; }),
      roles:        Array.from(document.querySelectorAll('input[name="role"]:checked')).map(function (c) { return c.value; }),
      availability: Array.from(document.querySelectorAll('input[name="availability"]:checked')).map(function (c) { return c.value; }),
      workTypes:    Array.from(document.querySelectorAll('input[name="workType"]:checked')).map(function (c) { return c.value; }),
      experience:   Array.from(document.querySelectorAll('input[name="experience"]:checked')).map(function (c) { return c.value; }),
      minRating:    parseFloat(document.querySelector('input[name="minRating"]:checked')?.value || '0'),
      skills:       Array.from(activeSkills),
      query:        heroSearchQuery
    };
  }

  /* ---- Card matches filter? ---- */
  function cardMatches (card, f) {
    var city    = card.dataset.city || '';
    var role    = card.dataset.role || '';
    var avail   = card.dataset.availability || '';
    var work    = card.dataset.workType || '';
    var exp     = card.dataset.experience || '';
    var rating  = parseFloat(card.dataset.rating || '0');
    var skills  = (card.dataset.skills || '').split(',').map(function (s) { return s.trim(); });
    var name    = (card.querySelector('.mc-name')?.textContent || '').toLowerCase();

    if (f.cities.length   && !f.cities.includes(city))   return false;
    if (f.roles.length    && !f.roles.includes(role))     return false;
    if (f.availability.length && !f.availability.includes(avail)) return false;
    if (f.workTypes.length) {
      var matched = f.workTypes.some(function (wt) { return work.includes(wt); });
      if (!matched) return false;
    }
    if (f.experience.length && !f.experience.includes(exp)) return false;
    if (rating < f.minRating) return false;
    if (f.skills.length && !f.skills.every(function (s) { return skills.includes(s); })) return false;
    if (f.query && !name.includes(f.query) && !(card.dataset.skills || '').toLowerCase().includes(f.query)) return false;

    return true;
  }

  /* ---- Sort ---- */
  function sortCards (arr) {
    var method = sortSelect ? sortSelect.value : 'rating';
    return arr.slice().sort(function (a, b) {
      if (method === 'rating')     return parseFloat(b.dataset.rating) - parseFloat(a.dataset.rating);
      if (method === 'experience') {
        var expOrder = { '10+': 4, '6-10': 3, '3-5': 2, '0-2': 1 };
        return (expOrder[b.dataset.experience] || 0) - (expOrder[a.dataset.experience] || 0);
      }
      if (method === 'reviews')    return parseInt(b.dataset.reviews) - parseInt(a.dataset.reviews);
      if (method === 'name') {
        var na = a.querySelector('.mc-name')?.textContent || '';
        var nb = b.querySelector('.mc-name')?.textContent || '';
        return na.localeCompare(nb);
      }
      return 0;
    });
  }

  /* ---- Pagination ---- */
  function renderPage () {
    var total   = filteredCards.length;
    var start   = (currentPage - 1) * CARDS_PER_PAGE;
    var end     = Math.min(start + CARDS_PER_PAGE, total);
    var visible = filteredCards.slice(start, end);

    cards.forEach(function (c) { c.hidden = true; });
    visible.forEach(function (c) { c.hidden = false; });

    /* Result count */
    if (resultsCount) {
      resultsCount.innerHTML = 'Showing <strong>' + visible.length + '</strong> of <strong>' + total + '</strong> verified maids';
    }

    /* No results state */
    if (noResults) noResults.hidden = total > 0;
    if (grid) grid.style.display = total > 0 ? '' : 'none';

    /* Pagination buttons */
    var totalPages = Math.ceil(total / CARDS_PER_PAGE);
    if (prevPage) prevPage.disabled = currentPage <= 1;
    if (nextPage) nextPage.disabled = currentPage >= totalPages;

    if (pageNumbers) {
      pageNumbers.innerHTML = '';
      for (var i = 1; i <= totalPages; i++) {
        var btn = document.createElement('button');
        btn.className = 'fam-page-num' + (i === currentPage ? ' active' : '');
        btn.textContent = i;
        btn.dataset.page = i;
        btn.addEventListener('click', function () {
          currentPage = parseInt(this.dataset.page, 10);
          renderPage();
          document.querySelector('.fam-main-section').scrollIntoView({ behavior: 'smooth' });
        });
        pageNumbers.appendChild(btn);
      }
    }
  }

  /* ---- Render active filter tags ---- */
  function renderTags (f) {
    if (!activeTagsEl) return;
    activeTagsEl.innerHTML = '';

    function makeTag (label, removeFn) {
      var tag = document.createElement('span');
      tag.className = 'fam-tag';
      tag.innerHTML = label;
      var x = document.createElement('button');
      x.innerHTML = '<i class="fa-solid fa-xmark"></i>';
      x.setAttribute('aria-label', 'Remove ' + label + ' filter');
      x.addEventListener('click', function () { removeFn(); applyFilters(); });
      tag.appendChild(x);
      activeTagsEl.appendChild(tag);
    }

    f.cities.forEach(function (v) {
      makeTag(v, function () {
        var cb = document.querySelector('input[name="city"][value="' + v + '"]');
        if (cb) cb.checked = false;
      });
    });
    f.roles.forEach(function (v) {
      makeTag(v, function () {
        var cb = document.querySelector('input[name="role"][value="' + v + '"]');
        if (cb) cb.checked = false;
      });
    });
    f.availability.forEach(function (v) {
      makeTag(v === 'available-now' ? 'Available Now' : 'Available Soon', function () {
        var cb = document.querySelector('input[name="availability"][value="' + v + '"]');
        if (cb) cb.checked = false;
      });
    });
    f.workTypes.forEach(function (v) {
      makeTag(v, function () {
        var cb = document.querySelector('input[name="workType"][value="' + v + '"]');
        if (cb) cb.checked = false;
      });
    });
    f.experience.forEach(function (v) {
      makeTag(v + ' yrs', function () {
        var cb = document.querySelector('input[name="experience"][value="' + v + '"]');
        if (cb) cb.checked = false;
      });
    });
    if (f.minRating > 0) {
      makeTag(f.minRating + '+ stars', function () {
        var rb = document.querySelector('input[name="minRating"][value="0"]');
        if (rb) rb.checked = true;
      });
    }
    f.skills.forEach(function (s) {
      makeTag(s, function () {
        activeSkills.delete(s);
        var btn = document.querySelector('.fam-skill-tag[data-skill="' + s + '"]');
        if (btn) btn.classList.remove('active');
      });
    });
    if (f.query) {
      makeTag('"' + f.query + '"', function () {
        heroSearchQuery = '';
        if (heroSearch) heroSearch.value = '';
      });
    }

    /* Update badge count */
    var count = activeTagsEl.querySelectorAll('.fam-tag').length;
    if (filterBadge) {
      filterBadge.textContent = count;
      filterBadge.hidden = count === 0;
    }
  }

  /* ---- Main apply function ---- */
  function applyFilters () {
    var f = getFilters();
    renderTags(f);
    filteredCards = sortCards(cards.filter(function (c) { return cardMatches(c, f); }));
    currentPage = 1;
    renderPage();
  }

  /* ---- Event listeners ---- */
  document.querySelectorAll('input[name="city"], input[name="role"], input[name="availability"], input[name="workType"], input[name="experience"], input[name="minRating"]')
    .forEach(function (el) { el.addEventListener('change', applyFilters); });

  if (sortSelect) sortSelect.addEventListener('change', applyFilters);

  if (clearAllBtn) clearAllBtn.addEventListener('click', clearAll);
  if (clearFromEmpty) clearFromEmpty.addEventListener('click', clearAll);

  function clearAll () {
    document.querySelectorAll('input[type="checkbox"]').forEach(function (cb) { cb.checked = false; });
    var any = document.querySelector('input[name="minRating"][value="0"]');
    if (any) any.checked = true;
    activeSkills.clear();
    skillTagBtns.forEach(function (b) { b.classList.remove('active'); });
    heroSearchQuery = '';
    if (heroSearch) heroSearch.value = '';
    if (heroCity)  heroCity.value  = '';
    if (heroRole)  heroRole.value  = '';
    applyFilters();
  }

  /* ---- Pagination nav buttons ---- */
  if (prevPage) {
    prevPage.addEventListener('click', function () {
      if (currentPage > 1) { currentPage--; renderPage(); document.querySelector('.fam-main-section').scrollIntoView({ behavior: 'smooth' }); }
    });
  }
  if (nextPage) {
    nextPage.addEventListener('click', function () {
      var totalPages = Math.ceil(filteredCards.length / CARDS_PER_PAGE);
      if (currentPage < totalPages) { currentPage++; renderPage(); document.querySelector('.fam-main-section').scrollIntoView({ behavior: 'smooth' }); }
    });
  }

  /* ---- View toggle ---- */
  if (viewGrid) {
    viewGrid.addEventListener('click', function () {
      grid.classList.remove('list-view');
      viewGrid.classList.add('active');
      viewList.classList.remove('active');
    });
  }
  if (viewList) {
    viewList.addEventListener('click', function () {
      grid.classList.add('list-view');
      viewList.classList.add('active');
      viewGrid.classList.remove('active');
    });
  }

  /* ---- Mobile sidebar toggle ---- */
  function openSidebar () {
    sidebar.classList.add('open');
    backdrop.classList.add('visible');
    mobileBtn.setAttribute('aria-expanded', 'true');
    document.body.style.overflow = 'hidden';
  }
  function closeSidebar () {
    sidebar.classList.remove('open');
    backdrop.classList.remove('visible');
    mobileBtn.setAttribute('aria-expanded', 'false');
    document.body.style.overflow = '';
  }
  if (mobileBtn) mobileBtn.addEventListener('click', openSidebar);
  if (backdrop)  backdrop.addEventListener('click', closeSidebar);
  if (applyBtn)  applyBtn.addEventListener('click', function () { applyFilters(); closeSidebar(); });

  /* ---- Initial render ---- */
  applyFilters();

})();
