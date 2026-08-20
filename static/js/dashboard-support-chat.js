(() => {
  'use strict';

  /* ── DOM refs ─────────────────────────────────────────── */
  const body            = document.body;
  const sidebar         = document.getElementById('sidebar');
  const sidebarOverlay  = document.getElementById('sidebarOverlay');
  const menuBtn         = document.getElementById('menuToggle');
  const convPanel       = document.getElementById('convPanel');
  const convOverlay     = document.getElementById('convOverlay');
  const convPanelToggle = document.getElementById('convPanelToggle');
  const backBtn         = document.getElementById('backBtn');
  const convList        = document.getElementById('convList');
  const convCount       = document.getElementById('convCount');
  const convSearch      = document.getElementById('convSearch');
  const msgBox          = document.getElementById('messages');
  const inputBar        = document.getElementById('inputBar');
  const noConvPH        = document.getElementById('noConvPlaceholder');
  const chatInput       = document.getElementById('chatInput');
  const sendBtn         = document.getElementById('sendBtn');
  const charCnt         = document.getElementById('charCount');
  const chatForm        = document.getElementById('chatForm');
  const resolveBtn      = document.getElementById('resolveBtn');
  const reopenBtn       = document.getElementById('reopenBtn');
  const resolvedBanner  = document.getElementById('resolvedBanner');
  const chatTitleName   = document.getElementById('chatTitleName');
  const chatTitleSub    = document.getElementById('chatTitleSub');
  const scrollBottomBtn = document.getElementById('scrollBottomBtn');

  if (!msgBox || !chatInput || !sendBtn) return;

  /* ── Config ───────────────────────────────────────────── */
  const apiUrl      = body.dataset.apiUrl;
  const convListUrl = body.dataset.convListUrl;
  const resolveUrl  = body.dataset.resolveUrl;
  const isStaff     = body.dataset.isStaff === '1';
  const initResolved = body.dataset.isResolved === '1';

  let activeEmployerId = body.dataset.employerId || '';
  let pollTimer        = null;
  let allConversations = [];
  let isResolved       = false;

  /* ── Mobile detection ─────────────────────────────────── */
  const isMobile = () => window.innerWidth <= 768;

  /* ── Helpers ──────────────────────────────────────────── */
  const getCookie = name =>
    document.cookie.split('; ').find(r => r.startsWith(name + '='))?.split('=')[1] || '';

  const scrollBottom = (smooth = true) =>
    msgBox.scrollTo({ top: msgBox.scrollHeight, behavior: smooth ? 'smooth' : 'auto' });

  const latestId = () =>
    [...msgBox.querySelectorAll('[data-message-id]')]
      .reduce((max, el) => Math.max(max, Number(el.dataset.messageId) || 0), 0);

  const renderedIds = new Set(
    [...(msgBox?.querySelectorAll('[data-message-id]') || [])]
      .map(el => Number(el.dataset.messageId))
  );

  function escHtml(str) {
    return String(str || '')
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  /* ══════════════════════════════════════════════════════
     MOBILE PANEL SWITCHING
     body.chat-open  → main visible, conv-panel hidden
     (default)       → conv-panel visible, main off-screen
  ══════════════════════════════════════════════════════ */
  function showChatPanel() {
    body.classList.add('chat-open');
  }

  function showConvPanel() {
    body.classList.remove('chat-open');
  }

  /* Back button — only visible on mobile */
  backBtn?.addEventListener('click', () => {
    showConvPanel();
    // Stop polling while viewing the list to save resources
    clearInterval(pollTimer);
    pollTimer = null;
    // Refresh conv list so badges are up-to-date
    if (isStaff) loadConversationList();
  });

  /* ── Sidebar toggle ───────────────────────────────────── */
  menuBtn?.addEventListener('click', () => {
    sidebar?.classList.toggle('open');
    sidebarOverlay?.classList.toggle('show');
  });
  sidebarOverlay?.addEventListener('click', () => {
    sidebar?.classList.remove('open');
    sidebarOverlay?.classList.remove('show');
  });

  /* Close sidebar via X button or nav link tap on mobile */
  document.getElementById('sidebarClose')?.addEventListener('click', () => {
    sidebar?.classList.remove('open');
    sidebarOverlay?.classList.remove('show');
  });
  sidebar?.querySelectorAll('.sidebar-nav a').forEach(link => {
    link.addEventListener('click', () => {
      if (window.innerWidth <= 768) {
        sidebar?.classList.remove('open');
        sidebarOverlay?.classList.remove('show');
      }
    });
  });

  /* ── Tablet conv-panel drawer toggle ─────────────────── */
  convPanelToggle?.addEventListener('click', () => {
    convPanel?.classList.toggle('open');
    convOverlay?.classList.toggle('show');
  });
  convOverlay?.addEventListener('click', () => {
    convPanel?.classList.remove('open');
    convOverlay?.classList.remove('show');
  });

  /* ══════════════════════════════════════════════════════
     CONVERSATION LIST
  ══════════════════════════════════════════════════════ */
  async function loadConversationList() {
    if (!convListUrl || !convList) return;
    try {
      const res  = await fetch(convListUrl, { headers: { Accept: 'application/json' } });
      if (!res.ok) return;
      const data = await res.json();
      allConversations = data.conversations || [];
      renderConvList(allConversations);
    } catch (_) { /* silent */ }
  }

  function renderConvList(convs) {
    if (convCount) convCount.textContent = convs.length;
    if (!convList) return;

    if (convs.length === 0) {
      convList.innerHTML = '<div class="conv-empty"><i class="fa-regular fa-comments"></i>No conversations yet.</div>';
      return;
    }

    convList.innerHTML = convs.map(c => `
      <div class="conv-item ${c.resolved ? 'resolved' : ''} ${String(c.employer_id) === String(activeEmployerId) ? 'active' : ''}"
           data-employer-id="${c.employer_id}"
           data-name="${escHtml(c.name)}"
           role="button" tabindex="0"
           aria-label="Conversation with ${escHtml(c.name)}">
        <div class="conv-avatar ${c.resolved ? 'resolved-avatar' : ''}">${escHtml(c.initials)}</div>
        <div class="conv-info">
          <div class="conv-name">${escHtml(c.name)}</div>
          <div class="conv-preview">${escHtml(c.last_message)}</div>
        </div>
        <div class="conv-meta">
          <span class="conv-time">${escHtml(c.last_time)}</span>
          ${c.unread > 0 ? `<span class="conv-badge">${c.unread}</span>` : ''}
          ${c.resolved   ? `<span class="conv-resolved-tag"><i class="fa-solid fa-circle-check"></i> Done</span>` : ''}
        </div>
      </div>
    `).join('');

    convList.querySelectorAll('.conv-item').forEach(item => {
      item.addEventListener('click',   () => selectConversation(item));
      item.addEventListener('keydown', e  => {
        if (e.key === 'Enter' || e.key === ' ') selectConversation(item);
      });
    });
  }

  /* ── Search ───────────────────────────────────────────── */
  convSearch?.addEventListener('input', () => {
    const q = convSearch.value.trim().toLowerCase();
    renderConvList(q ? allConversations.filter(c => c.name.toLowerCase().includes(q)) : allConversations);
  });

  /* ── Select a conversation ────────────────────────────── */
  function selectConversation(item) {
    const eid  = item.dataset.employerId;
    const name = item.dataset.name;

    const alreadyActive = String(eid) === String(activeEmployerId);

    activeEmployerId = eid;

    // Highlight in list
    convList?.querySelectorAll('.conv-item').forEach(el =>
      el.classList.toggle('active', el.dataset.employerId === eid)
    );

    // Update topbar title
    if (chatTitleName) chatTitleName.textContent = name;
    if (chatTitleSub)  chatTitleSub.textContent  = 'Live support';

    // Show chat UI
    if (noConvPH)  noConvPH.style.display  = 'none';
    if (msgBox)    msgBox.style.display    = 'flex';
    if (inputBar)  inputBar.style.display  = 'block';
    if (resolveBtn) resolveBtn.style.display = 'flex';

    // Enable input
    chatInput.disabled    = false;
    chatInput.placeholder = 'Write a message…';

    // Resolved state from cache
    const conv = allConversations.find(c => String(c.employer_id) === String(eid));
    setResolvedUI(conv ? conv.resolved : false);

    // On mobile: slide to chat panel
    if (isMobile()) {
      showChatPanel();
    } else {
      // Tablet: close drawer
      convPanel?.classList.remove('open');
      convOverlay?.classList.remove('show');
    }

    // If same conversation already loaded, don't wipe messages
    if (!alreadyActive) {
      msgBox.innerHTML = `
        <div class="sys-msg">
          <i class="fa-solid fa-shield-halved" style="color:var(--accent);"></i>
          &nbsp;SelectRoyalMaids live support
        </div>
        <div class="date-divider">Today</div>
      `;
      renderedIds.clear();
      loadMessages(true);
    }

    // (Re)start polling
    clearInterval(pollTimer);
    pollTimer = setInterval(pollMessages, 3000);
  }

  /* ══════════════════════════════════════════════════════
     MESSAGES
  ══════════════════════════════════════════════════════ */
  function appendBubble({ id, sender, initials, body: bodyText, outgoing, time }) {
    if (id && renderedIds.has(Number(id))) return;
    if (id) renderedIds.add(Number(id));

    const row = document.createElement('div');
    row.className = `msg-row ${outgoing ? 'outgoing' : 'incoming'}`;
    if (id) row.dataset.messageId = id;

    const avatar  = `<div class="msg-avatar ${outgoing ? 'out' : 'in'}">${escHtml(initials)}</div>`;
    const content = `
      <div class="msg-content">
        <div class="msg-meta">${outgoing ? 'You' : escHtml(sender)}</div>
        <div class="msg-bubble"></div>
        <span class="msg-time">${escHtml(time)}</span>
      </div>`;

    row.innerHTML = outgoing ? `${content}${avatar}` : `${avatar}${content}`;
    row.querySelector('.msg-bubble').innerHTML = bodyText; // server-generated, safe
    msgBox.appendChild(row);
    scrollBottom();
  }

  async function loadMessages(initial = false) {
    if (!apiUrl || !activeEmployerId) return;
    try {
      const after = initial ? 0 : latestId();
      const res   = await fetch(
        `${apiUrl}?employer=${encodeURIComponent(activeEmployerId)}&after=${after}`,
        { headers: { Accept: 'application/json' } }
      );
      if (!res.ok) return;
      const data = await res.json();
      data.messages.forEach(m => appendBubble(m));
      if (initial) scrollBottom(false);
    } catch (_) { /* silent */ }
  }

  async function pollMessages() {
    if (!activeEmployerId) return;
    await loadMessages(false);
    if (isStaff) loadConversationList();
  }

  /* ── Send ─────────────────────────────────────────────── */
  chatInput.addEventListener('input', () => {
    chatInput.style.height = 'auto';
    chatInput.style.height = Math.min(chatInput.scrollHeight, 120) + 'px';
    if (charCnt) charCnt.textContent = chatInput.value.length;
    sendBtn.disabled = !chatInput.value.trim();
  });

  chatInput.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (!sendBtn.disabled) chatForm.requestSubmit();
    }
  });

  chatForm.addEventListener('submit', async e => {
    e.preventDefault();
    const bodyText = chatInput.value.trim();
    if (!bodyText || !apiUrl || !activeEmployerId) return;

    sendBtn.disabled = true;
    try {
      const form = new URLSearchParams({ body: bodyText, employer: activeEmployerId });
      const res  = await fetch(apiUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
          'X-CSRFToken':  decodeURIComponent(getCookie('csrftoken')),
          Accept:         'application/json',
        },
        body: form,
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Unable to send message.');
      appendBubble(data.message);
      chatInput.value = '';
      chatInput.style.height = 'auto';
      if (charCnt) charCnt.textContent = '0';
      chatInput.focus();
      if (isStaff) loadConversationList();
    } catch (err) {
      appendSystemMsg('fa-triangle-exclamation', err.message || 'Unable to send message.');
    } finally {
      sendBtn.disabled = !chatInput.value.trim();
    }
  });

  function appendSystemMsg(iconClass, text) {
    const div = document.createElement('div');
    div.className = 'sys-msg';
    div.innerHTML = `<i class="fa-solid ${iconClass}" style="color:#dc2626;"></i>&nbsp;${escHtml(text)}`;
    msgBox.appendChild(div);
    scrollBottom();
  }

  /* ══════════════════════════════════════════════════════
     RESOLVE / REOPEN
  ══════════════════════════════════════════════════════ */
  function setResolvedUI(resolved) {
    isResolved = resolved;
    if (resolvedBanner) resolvedBanner.classList.toggle('show', resolved);
    if (!resolveBtn) return;
    if (resolved) {
      resolveBtn.className = 'icon-btn resolved-btn';
      resolveBtn.innerHTML = '<i class="fa-solid fa-rotate-left"></i><span>Reopen</span>';
      resolveBtn.title     = 'Reopen this conversation';
    } else {
      resolveBtn.className = 'icon-btn resolve-btn';
      resolveBtn.innerHTML = '<i class="fa-solid fa-circle-check"></i><span>Mark Resolved</span>';
      resolveBtn.title     = 'Mark as resolved';
    }
  }

  async function toggleResolve() {
    if (!resolveUrl || !activeEmployerId) return;
    try {
      const action = isResolved ? 'reopen' : 'resolve';
      const res    = await fetch(resolveUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
          'X-CSRFToken':  decodeURIComponent(getCookie('csrftoken')),
          Accept:         'application/json',
        },
        body: new URLSearchParams({ employer: activeEmployerId, action }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Action failed.');
      setResolvedUI(data.resolved);
      const conv = allConversations.find(c => String(c.employer_id) === String(activeEmployerId));
      if (conv) conv.resolved = data.resolved;
      renderConvList(allConversations);
      appendSystemMsg(
        data.resolved ? 'fa-circle-check' : 'fa-rotate-left',
        data.resolved ? 'Conversation marked as resolved.' : 'Conversation reopened.'
      );
    } catch (err) {
      appendSystemMsg('fa-triangle-exclamation', err.message);
    }
  }

  resolveBtn?.addEventListener('click', toggleResolve);
  reopenBtn?.addEventListener('click',  toggleResolve);
  scrollBottomBtn?.addEventListener('click', () => scrollBottom());

  /* ══════════════════════════════════════════════════════
     INIT
  ══════════════════════════════════════════════════════ */
  function init() {
    if (isStaff) {
      // Admin: load conv list first
      loadConversationList();

      if (activeEmployerId) {
        // Pre-selected via ?employer= query param
        if (chatTitleName) chatTitleName.textContent = 'Loading…';
        if (noConvPH)  noConvPH.style.display  = 'none';
        if (msgBox)    msgBox.style.display    = 'flex';
        if (inputBar)  inputBar.style.display  = 'block';
        if (resolveBtn) resolveBtn.style.display = 'flex';
        chatInput.disabled = false;
        setResolvedUI(initResolved);
        scrollBottom(false);
        pollTimer = setInterval(pollMessages, 3000);

        // On mobile, go straight to chat since a conv is already selected
        if (isMobile()) showChatPanel();
      } else {
        // No conv selected yet — show the list (default state on mobile)
        if (noConvPH)  noConvPH.style.display  = 'flex';
        if (msgBox)    msgBox.style.display    = 'none';
        if (inputBar)  inputBar.style.display  = 'none';
        if (resolveBtn) resolveBtn.style.display = 'none';
        // On mobile: conv list is already the default visible panel (no chat-open class)
        // On desktop: placeholder is shown inside .main
      }
    } else {
      // Employer: single conversation, go straight to chat
      if (noConvPH)  noConvPH.style.display = 'none';
      if (msgBox)    msgBox.style.display   = 'flex';
      if (inputBar)  inputBar.style.display = 'block';
      chatInput.disabled    = false;
      chatInput.placeholder = 'Write a message…';
      setResolvedUI(initResolved);
      scrollBottom(false);
      // Employer has no conv panel so .main is always left:0 — no panel swap needed
      if (activeEmployerId) {
        pollTimer = setInterval(pollMessages, 3000);
      }
    }
  }

  init();
})();
