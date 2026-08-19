(() => {
  'use strict';
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('sidebarOverlay');
  const menuBtn = document.getElementById('menuToggle');
  const msgBox = document.getElementById('messages');
  const input = document.getElementById('chatInput');
  const sendBtn = document.getElementById('sendBtn');
  const charCnt = document.getElementById('charCount');
  const typing = document.getElementById('typingIndicator');
  if (!sidebar || !overlay || !menuBtn || !msgBox || !input || !sendBtn) return;

  const meName = document.body.dataset.chatUserName || '';
  const apiUrl = document.body.dataset.apiUrl;
  const employerId = document.body.dataset.employerId;
  menuBtn.addEventListener('click', () => { sidebar.classList.toggle('open'); overlay.classList.toggle('show'); });
  overlay.addEventListener('click', () => { sidebar.classList.remove('open'); overlay.classList.remove('show'); });

  const scrollBottom = (smooth = true) => msgBox.scrollTo({ top: msgBox.scrollHeight, behavior: smooth ? 'smooth' : 'auto' });
  const nowTime = () => new Date().toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });

  // Track every message ID already in the DOM (server-rendered + JS-added)
  const renderedIds = new Set(
    [...msgBox.querySelectorAll('[data-message-id]')].map(el => Number(el.dataset.messageId))
  );

  const appendSystemMessage = (iconClass, statusClass, text) => {
    const message = document.createElement('div');
    message.className = 'sys-msg';
    const icon = document.createElement('i');
    icon.className = `fa-solid ${iconClass} ${statusClass}`;
    message.append(icon, document.createTextNode(`  ${text}`));
    msgBox.appendChild(message);
    scrollBottom();
  };
  const appendBubble = ({ id, sender, initials, body, outgoing, time }) => {
    // Skip if already rendered (prevents duplicates from overlapping poll + send)
    if (id && renderedIds.has(Number(id))) return;
    if (id) renderedIds.add(Number(id));
    const row = document.createElement('div');
    row.className = `msg-row js-added ${outgoing ? 'outgoing' : 'incoming'}`;
    row.dataset.messageId = id;
    const avatar = `<div class="msg-avatar ${outgoing ? 'out' : 'in'}">${initials}</div>`;
    const meta = `<div class="msg-meta">${outgoing ? 'You' : sender}</div>`;
    const bubble = '<div class="msg-bubble"></div>';
    const stamp = `<span class="msg-time">${time}</span>`;
    row.innerHTML = outgoing ? `<div>${meta}${bubble}</div>${avatar}${stamp}` : `${avatar}<div>${meta}${bubble}</div>${stamp}`;
    row.querySelector('.msg-bubble').innerHTML = body;
    msgBox.appendChild(row);
    scrollBottom();
  };

  input.addEventListener('input', () => {
    input.style.height = 'auto';
    input.style.height = `${Math.min(input.scrollHeight, 120)}px`;
    charCnt.textContent = input.value.length;
    sendBtn.disabled = !input.value.trim();
  });
  input.addEventListener('keydown', event => {
    if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); if (!sendBtn.disabled) document.getElementById('chatForm').requestSubmit(); }
  });

  const getCookie = name => document.cookie.split('; ').find(row => row.startsWith(`${name}=`))?.split('=')[1] || '';
  const withEmployer = url => employerId ? `${url}?employer=${encodeURIComponent(employerId)}` : url;
  const latestId = () => [...msgBox.querySelectorAll('[data-message-id]')].reduce((max, item) => Math.max(max, Number(item.dataset.messageId) || 0), 0);
  const syncMessages = async () => {
    if (!apiUrl || !employerId) return;
    try {
      const response = await fetch(`${withEmployer(apiUrl)}&after=${latestId()}`, { headers: { Accept: 'application/json' } });
      if (!response.ok) return;
      const data = await response.json();
      data.messages.forEach(message => appendBubble(message));
    } catch (_) { /* A later poll will retry without disrupting the chat. */ }
  };
  document.getElementById('chatForm').addEventListener('submit', async event => {
    event.preventDefault();
    const body = input.value.trim();
    if (!body || !apiUrl || !employerId) return;
    sendBtn.disabled = true;
    try {
      const form = new URLSearchParams({ body, employer: employerId });
      const response = await fetch(apiUrl, { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8', 'X-CSRFToken': decodeURIComponent(getCookie('csrftoken')), Accept: 'application/json' }, body: form });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Unable to send message.');
      appendBubble(data.message);
      input.value = ''; input.style.height = 'auto'; charCnt.textContent = '0'; input.focus();
    } catch (error) { appendSystemMessage('fa-triangle-exclamation', 'chat-status-warning', error.message || 'Unable to send message.'); }
    finally { sendBtn.disabled = !input.value.trim(); }
  });
  document.getElementById('scrollBottomBtn').addEventListener('click', () => scrollBottom());
  document.getElementById('clearBtn').addEventListener('click', () => msgBox.querySelectorAll('.msg-row.js-added').forEach(element => element.remove()));
  document.getElementById('employerPicker')?.addEventListener('change', event => {
    window.location.assign(event.target.value ? `${location.pathname}?employer=${encodeURIComponent(event.target.value)}` : location.pathname);
  });
  scrollBottom(false);
  window.setInterval(syncMessages, 3000);
})();
