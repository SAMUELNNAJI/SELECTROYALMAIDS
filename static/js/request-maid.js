/* ============================================================
   REQUEST A MAID  –  multi-step form logic
   ============================================================ */
(function () {

  const TOTAL_STEPS = 5;
  let currentStep = 1;

  const tabs      = document.querySelectorAll('.rm-tab');
  const steps     = document.querySelectorAll('.rm-step');
  const progress  = document.getElementById('rmProgress');
  const backBtn   = document.getElementById('rmBack');
  const nextBtn   = document.getElementById('rmNext');
  const indicator = document.getElementById('rmStepIndicator');
  const card      = document.getElementById('rmCard');
  const success   = document.getElementById('rmSuccess');
  const submitUrl = card?.dataset.submitUrl;

  /* Sync service radio cards with the select dropdown */
  const serviceRadios = document.querySelectorAll('input[name="service"]');
  const serviceSelect = document.getElementById('serviceSelect');

  serviceRadios.forEach(r => {
    r.addEventListener('change', () => {
      serviceSelect.value = r.value;
    });
  });
  serviceSelect.addEventListener('change', () => {
    serviceRadios.forEach(r => {
      r.checked = r.value === serviceSelect.value;
    });
  });

  /* ---- Navigate to a step ---- */
  function goTo(step) {
    // Update steps
    steps.forEach(s => s.classList.toggle('active', +s.dataset.step === step));

    // Update tabs
    tabs.forEach(t => {
      const n = +t.dataset.step;
      t.classList.remove('active', 'done');
      if (n === step)       t.classList.add('active');
      else if (n < step)    t.classList.add('done');
    });

    // Progress bar
    progress.style.width = ((step / TOTAL_STEPS) * 100) + '%';

    // Indicator
    indicator.textContent = `Step ${step} of ${TOTAL_STEPS}`;

    // Back button
    backBtn.disabled = step === 1;

    // Next / Submit button
    if (step === TOTAL_STEPS) {
      nextBtn.textContent = '';
      nextBtn.innerHTML = '<i class="fa-solid fa-paper-plane"></i> Submit Request';
      nextBtn.classList.add('rm-btn--submit');
      nextBtn.classList.remove('rm-btn--next');
      // Populate review
      populateReview();
    } else {
      nextBtn.innerHTML = 'Continue <i class="fa-solid fa-arrow-right"></i>';
      nextBtn.classList.add('rm-btn--next');
      nextBtn.classList.remove('rm-btn--submit');
    }

    currentStep = step;

    // Scroll to top of card
    card.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  /* ---- Validate current step ---- */
  function validateStep(step) {
    if (step === 1) {
      const chosen = document.querySelector('input[name="service"]:checked');
      const sel    = document.getElementById('serviceSelect').value;
      if (!chosen && !sel) {
        showError('Please select a service to continue.');
        return false;
      }
    }
    if (step === 2) {
      const state   = document.getElementById('stateField').value;
      const city    = document.getElementById('cityField').value.trim();
      const address = document.getElementById('addressField').value.trim();
      if (!state)   { showError('Please select your state.'); return false; }
      if (!city)    { showError('Please enter your city / area.'); return false; }
      if (!address) { showError('Please enter your address.'); return false; }
    }
    if (step === 3) {
      const budget = document.getElementById('budgetField').value;
      if (!budget) { showError('Please select a budget range.'); return false; }
    }
    if (step === 4) {
      const name  = document.getElementById('fullNameField').value.trim();
      const phone = document.getElementById('phoneField').value.trim();
      const email = document.getElementById('emailField').value.trim();
      const start = document.getElementById('startDateField').value;
      if (!name)  { showError('Please enter your full name.'); return false; }
      if (!phone) { showError('Please enter your phone number.'); return false; }
      if (!email) { showError('Please enter your email address.'); return false; }
      if (!start) { showError('Please select a preferred start date.'); return false; }
    }
    if (step === 5) {
      const terms = document.getElementById('termsCheck').checked;
      if (!terms) { showError('Please agree to the Terms of Service and Privacy Policy.'); return false; }
    }
    return true;
  }

  /* ---- Show error ---- */
  function showError(msg) {
    // Remove any existing error
    const prev = card.querySelector('.rm-error-msg');
    if (prev) prev.remove();

    const el = document.createElement('div');
    el.className = 'rm-error-msg';
    el.innerHTML = `<i class="fa-solid fa-circle-exclamation"></i> ${msg}`;

    const nav = card.querySelector('.rm-step-nav');
    card.insertBefore(el, nav);

    el.scrollIntoView({ behavior: 'smooth', block: 'center' });

    setTimeout(() => { if (el.parentNode) el.remove(); }, 4000);
  }

  /* ---- Populate review ---- */
  function populateReview() {
    const grid = document.getElementById('rmReviewGrid');
    if (!grid) return;

    const service  = (document.querySelector('input[name="service"]:checked')?.value
                   || document.getElementById('serviceSelect').value
                   || '—');
    const state    = document.getElementById('stateField').value    || '—';
    const city     = document.getElementById('cityField').value     || '—';
    const address  = document.getElementById('addressField').value  || '—';
    const worktype = document.querySelector('input[name="worktype"]:checked')?.value || '—';
    const budget   = document.getElementById('budgetField').value   || '—';
    const start    = document.getElementById('startDateField').value || '—';
    const name     = document.getElementById('fullNameField').value  || '—';
    const phone    = document.getElementById('phoneField').value     || '—';
    const email    = document.getElementById('emailField').value     || '—';
    const skills   = [...document.querySelectorAll('.rm-checkbox-group input:checked')]
                       .map(c => c.value).join(', ') || '—';

    const items = [
      { label: 'Service',      value: capitalise(service) },
      { label: 'State',        value: state },
      { label: 'City / Area',  value: city },
      { label: 'Address',      value: address },
      { label: 'Work Type',    value: capitalise(worktype) },
      { label: 'Budget',       value: budget },
      { label: 'Start Date',   value: start },
      { label: 'Skills',       value: skills },
      { label: 'Name',         value: name },
      { label: 'Phone',        value: phone },
      { label: 'Email',        value: email },
    ];

    grid.innerHTML = items.map(i => `
      <div class="rm-review-item">
        <div class="rm-review-item-label">${i.label}</div>
        <div class="rm-review-item-value">${i.value}</div>
      </div>
    `).join('');
  }

  function capitalise(str) {
    return str.charAt(0).toUpperCase() + str.slice(1).replace(/-/g, ' ');
  }

  const selectedValue = selector => document.querySelector(selector)?.value || '';
  const selectedLabels = selector => [...document.querySelectorAll(selector)]
    .filter(input => input.checked)
    .map(input => input.closest('label')?.querySelector('span')?.textContent.trim() || input.value);
  const csrfToken = () => document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';

  async function submitRequest() {
    const service = selectedValue('input[name="service"]') || serviceSelect.value;
    const payload = {
      service: capitalise(service),
      state: document.getElementById('stateField').value,
      city: document.getElementById('cityField').value.trim(),
      address: document.getElementById('addressField').value.trim(),
      landmark: document.getElementById('landmarkField').value.trim(),
      worktype: capitalise(selectedValue('input[name="worktype"]')),
      experience: document.getElementById('experienceField').value,
      skills: selectedLabels('.rm-step[data-step="3"] .rm-checkbox-group input').join(', '),
      gender_preference: document.getElementById('genderPref').value,
      budget: document.getElementById('budgetField').value,
      notes: document.getElementById('notesField').value.trim(),
      start_date: document.getElementById('startDateField').value,
      urgency: document.getElementById('urgencyField').value,
      interview_method: capitalise(selectedValue('input[name="interview"]')),
      interview_days: selectedLabels('.rm-step[data-step="4"] .rm-checkbox-group input').join(', '),
      contact_name: document.getElementById('fullNameField').value.trim(),
      contact_phone: document.getElementById('phoneField').value.trim(),
      contact_email: document.getElementById('emailField').value.trim(),
    };
    const response = await fetch(submitUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8', 'X-CSRFToken': csrfToken(), Accept: 'application/json' },
      body: new URLSearchParams(payload),
      redirect: 'manual',
    });
    if (response.status === 302 || response.status === 301) {
      const location = response.headers.get('Location');
      window.location.href = location || submitUrl;
      return;
    }
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new Error(data.error || 'We could not submit your request. Please try again.');
    }
    return response.json();
  }

  /* ---- Button events ---- */
  nextBtn.addEventListener('click', async () => {
    if (!validateStep(currentStep)) return;

    if (currentStep === TOTAL_STEPS) {
      nextBtn.disabled = true;
      nextBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Submitting…';
      try {
        const result = await submitRequest();
        card.hidden = true;
        success.hidden = false;
        const chatLink = document.createElement('a');
        chatLink.href = result.chat_url;
        chatLink.className = 'btn btn-primary btn-lg';
        chatLink.innerHTML = '<i class="fa-solid fa-comments"></i> Open Support Chat';
        success.querySelector('.rm-success-actions')?.prepend(chatLink);
        success.scrollIntoView({ behavior: 'smooth', block: 'start' });
      } catch (error) {
        showError(error.message);
        nextBtn.disabled = false;
        nextBtn.innerHTML = '<i class="fa-solid fa-paper-plane"></i> Submit Request';
      }
      return;
    }
    goTo(currentStep + 1);
  });

  backBtn.addEventListener('click', () => {
    if (currentStep > 1) goTo(currentStep - 1);
  });

  /* ---- Init ---- */
  goTo(1);

  /* Error message style (injected once) */
  const errStyle = document.createElement('style');
  errStyle.textContent = `
    .rm-error-msg {
      display: flex;
      align-items: center;
      gap: 8px;
      background: #fef2f2;
      border: 1px solid #fecaca;
      color: #b91c1c;
      font-size: 13px;
      font-weight: 600;
      padding: 10px 16px;
      border-radius: 10px;
      margin-top: 8px;
      margin-bottom: 0;
      animation: rmFadeIn .25s ease;
    }
    .rm-error-msg i { font-size: 14px; flex-shrink: 0; }
  `;
  document.head.appendChild(errStyle);

})();
