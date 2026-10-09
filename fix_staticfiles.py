#!/usr/bin/env python
"""Sync the staticfiles/js/ copy with the functional changes in static/js/."""

p = 'staticfiles/js/dashboard-support-chat.js'
with open(p, encoding='utf-8') as f:
    c = f.read()

# 1. Add sanitizeHtml after escHtml block
old_esc = (
    "  function escHtml(str) {\n"
    "    return String(str || '')\n"
    "      .replace(/&/g, '&amp;').replace(/</g, '&lt;')\n"
    '      .replace(/>/g, "&gt;").replace(/"/g, "&quot;");\n'
    '  }\n'
    "\n"
    '  /* ══════════════════════════════════════════════════════\n'
    '     MOBILE PANEL SWITCHING'
)

new_esc = (
    '  function escHtml(str) {\n'
    "    return String(str || '')\n"
    "      .replace(/&/g, '&amp;').replace(/</g, '&lt;')\n"
    '      .replace(/>/g, "&gt;").replace(/"/g, "&quot;");\n'
    '  }\n'
    '\n'
    '  /* ── Sanitize server HTML for the chat bubble ────────────────── */\n'
    '  // Only a safe subset of tags & attributes is permitted.  Everything else is\n'
    '  // stripped so that user-supplied content can never inject markup into the DOM.\n'
    "  const SAFE_TAGS = ['b','strong','i','em','u','br','p','ul','ol','li','a','span','div','h1','h2','h3','blockquote','img','table','thead','tbody','tr','th','td'];\n"
    "  const SAFE_ATTRS = ['href','title','alt'];\n"
    '\n'
    '  function sanitizeHtml(dirty) {\n'
    '    const tmp = document.createElement(\'div\');\n'
    "    tmp.innerHTML = dirty || '';\n"
    '    const nodes = [];\n'
    '    const walker = document.createTreeWalker(tmp, NodeFilter.SHOW_ELEMENT);\n'
    '    let el;\n'
    '    while (el = walker.nextNode()) nodes.push(el);\n'
    '    for (const node of nodes) {\n'
    '      const tag = node.tagName.toLowerCase();\n'
    '      if (!SAFE_TAGS.includes(tag)) {\n'
    '        while (node.firstChild) node.parentNode.insertBefore(node.firstChild, node);\n'
    '        node.remove();\n'
    '        continue;\n'
    '      }\n'
    '      [...node.attributes].forEach(attr => {\n'
    "        if (!SAFE_ATTRS.includes(attr.name.toLowerCase())) node.removeAttribute(attr.name);\n"
    '      });\n'
    '    }\n'
    '    return tmp.innerHTML;\n'
    '  }\n'
    '\n'
    '  /* ══════════════════════════════════════════════════════\n'
    '     MOBILE PANEL SWITCHING'
)

if old_esc in c:
    c = c.replace(old_esc, new_esc, 1)
    print("Added sanitizeHtml function")
else:
    print("WARNING: escHtml block not found — may already be patched")

# 2. Update renderConvList preview line
old_preview = 'escHtml(c.last_message)'
new_preview = 'escHtml(c.body_text || c.last_message || \'\')'
if old_preview in c:
    c = c.replace(old_preview, new_preview, 1)
    print("Updated conv-list preview")
else:
    print("WARNING: preview line not found")

# 3. Update appendBubble to use sanitizeHtml
old_bubble = 'row.querySelector(\'.msg-bubble\').innerHTML = bodyText; // server-generated, safe'
new_bubble = 'row.querySelector(\'.msg-bubble\').innerHTML = sanitizeHtml(bodyText); // sanitize server HTML'
if old_bubble in c:
    c = c.replace(old_bubble, new_bubble, 1)
    print("Updated appendBubble sanitization")
else:
    print("WARNING: appendBubble line not found")

with open(p, 'w', encoding='utf-8') as f:
    f.write(c)
print("Done")
