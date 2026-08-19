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
  menuBtn.addEventListener('click', () => { sidebar.classList.toggle('open'); overlay.classList.toggle('show'); });
  overlay.addEventListener('click', () => { sidebar.classList.remove('open'); overlay.classList.remove('show'); });

  const scrollBottom = (smooth = true) => msgBox.scrollTo({ top: msgBox.scrollHeight, behavior: smooth ? 'smooth' : 'auto' });
  const nowTime = () => new Date().toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
  const appendSystemMessage = (iconClass, statusClass, text) => {
    const message = document.createElement('div');
    message.className = 'sys-msg';
    const icon = document.createElement('i');
    icon.className = `fa-solid ${iconClass} ${statusClass}`;
    message.append(icon, document.createTextNode(`  ${text}`));
    msgBox.appendChild(message);
    scrollBottom();
  };
  const appendBubble = ({ sender, initials, body, outgoing, time }) => {
    const row = document.createElement('div');
    row.className = `msg-row js-added ${outgoing ? 'outgoing' : 'incoming'}`;
    const avatar = `<div class="msg-avatar ${outgoing ? 'out' : 'in'}">${initials}</div>`;
    const meta = `<div class="msg-meta">${outgoing ? 'You' : sender}</div>`;
    const bubble = '<div class="msg-bubble"></div>';
    const stamp = `<span class="msg-time">${time}</span>`;
    row.innerHTML = outgoing ? `<div>${meta}${bubble}</div>${avatar}${stamp}` : `${avatar}<div>${meta}${bubble}</div>${stamp}`;
    row.querySelector('.msg-bubble').textContent = body;
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

  const proto = location.protocol === 'https:' ? 'wss://' : 'ws://';
  const socket = new WebSocket(`${proto}${location.host}/ws/support-chat/`);
  socket.onclose = () => appendSystemMessage('fa-plug-circle-xmark', 'chat-status-error', 'Connection lost. Please refresh.');
  socket.onerror = () => appendSystemMessage('fa-triangle-exclamation', 'chat-status-warning', 'Could not connect to chat server.');
  socket.onmessage = event => {
    const data = JSON.parse(event.data);
    typing.classList.remove('show');
    appendBubble({ sender: data.sender, initials: data.initials || data.sender.slice(0, 2).toUpperCase(), body: data.body, outgoing: data.sender === meName, time: data.time || nowTime() });
  };
  document.getElementById('chatForm').addEventListener('submit', event => {
    event.preventDefault();
    const body = input.value.trim();
    if (!body || socket.readyState !== WebSocket.OPEN) return;
    socket.send(JSON.stringify({ body }));
    input.value = ''; input.style.height = 'auto'; charCnt.textContent = '0'; sendBtn.disabled = true; input.focus();
  });
  document.getElementById('scrollBottomBtn').addEventListener('click', () => scrollBottom());
  document.getElementById('clearBtn').addEventListener('click', () => msgBox.querySelectorAll('.msg-row.js-added').forEach(element => element.remove()));
  scrollBottom(false);
})();
