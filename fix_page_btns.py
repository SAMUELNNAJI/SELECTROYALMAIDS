import os, re

css_dir = 'static/css'

# Files with hardcoded primary submit / CTA buttons that should be gold #C5952E
# After first pass, #2563eb became #001F3F - now we fix specific button selectors

button_selectors = [
    # contact.css
    ('.cf-submit {', 'background: #001F3F;', 'background: #C5952E;'),
    ('.cf-submit:hover { background: #001F3F;', 'background: #001F3F;', 'background: #A87A22;'),
    # request-maid.css
    ('.rm-btn--next {', 'background: #001F3F;', 'background: #C5952E;'),
    ('.rm-btn--next:hover { background: #001F3F;', 'background: #001F3F;', 'background: #A87A22;'),
    # register-as-maid.css - .ram-submit uses btn class
    # auth.css
    ('.af-submit {', 'background: #001F3F;', 'background: #C5952E;'),
    ('.af-submit:hover { background: #001F3F;', 'background: #001F3F;', 'background: #A87A22;'),
    # find-a-maid.css skill tag active
    ('.fam-skill-tag.active {', 'background: var(--blue);', 'background: #C5952E;'),
    # view toggle active
    ('.fam-view-btn.active,\n.fam-view-btn:hover { background: var(--blue);', 'background: var(--blue);', 'background: #C5952E;'),
]

# Simpler approach: just do targeted replacements per file
file_replacements = {
    'contact.css': [
        ('.cf-submit {\n  width: 100%;\n  padding: 14px;\n  background: #001F3F;',
         '.cf-submit {\n  width: 100%;\n  padding: 14px;\n  background: #C5952E;'),
        ('.cf-submit:hover { background: #001F3F;',
         '.cf-submit:hover { background: #A87A22;'),
        ('.cf-chip:hover,\n.cf-chip.active {\n  border-color: #001F3F;\n  color: #001F3F;',
         '.cf-chip:hover,\n.cf-chip.active {\n  border-color: #C5952E;\n  color: #C5952E;'),
        ('.cs-hours-block {\n  background: linear-gradient(135deg, #001F3F 0%, #001F3F 100%);',
         '.cs-hours-block {\n  background: linear-gradient(135deg, #001F3F 0%, #00305F 100%);'),
    ],
    'request-maid.css': [
        ('background: #001F3F;\n  color: #fff;\n  border-color: #001F3F;\n  padding: 11px 28px;\n}\n.rm-btn--next:hover { background: #001F3F;',
         'background: #C5952E;\n  color: #fff;\n  border-color: #C5952E;\n  padding: 11px 28px;\n}\n.rm-btn--next:hover { background: #A87A22;'),
        # active tab
        ('.rm-tab.active {\n  background: #001F3F;\n  color: #fff;\n  border-color: #001F3F;\n}',
         '.rm-tab.active {\n  background: #001F3F;\n  color: #fff;\n  border-color: #001F3F;\n}'),
        # rm-btn--next border-color hover
        ('.rm-btn--back:hover:not(:disabled) {\n  border-color: #001F3F;\n  color: #001F3F;',
         '.rm-btn--back:hover:not(:disabled) {\n  border-color: #001F3F;\n  color: #001F3F;'),
    ],
    'auth.css': [
        ('.af-submit {\n  width: 100%;\n  padding: 13px;\n  background: #001F3F;',
         '.af-submit {\n  width: 100%;\n  padding: 13px;\n  background: #C5952E;'),
        ('.af-submit:hover { background: #001F3F;',
         '.af-submit:hover { background: #A87A22;'),
        # login type tab active
        ('.login-type-tab.active { background: #001F3F; color: #fff; }',
         '.login-type-tab.active { background: #001F3F; color: #fff; }'),
    ],
}

files_changed = []
for fname, repls in file_replacements.items():
    path = os.path.join(css_dir, fname)
    if not os.path.exists(path):
        continue
    with open(path, encoding='utf-8') as f:
        content = f.read()
    original = content
    for old, new in repls:
        content = content.replace(old, new)
    if content != original:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        files_changed.append(fname)

print('Done. Changed:', files_changed)
