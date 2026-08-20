import os

css_dir = 'static/css'

# (old, new) — straight string replacements, applied in order
replacements = [
    # CSS variable definitions
    ('--blue: #2563eb',   '--blue: #001F3F'),
    ('--blue-dark: #1d4ed8', '--blue-dark: #001F3F'),
    ('--blue-light: #eff6ff', '--blue-light: #EEF4FA'),
    ('--blue-mid: #3b82f6', '--blue-mid: #4A7FA5'),
    ('--accent: #2563eb', '--accent: #001F3F'),

    # rgba shadows (blue -> navy)
    ('rgba(37,99,235,.06)',  'rgba(0,31,63,.06)'),
    ('rgba(37,99,235,.08)',  'rgba(0,31,63,.08)'),
    ('rgba(37,99,235,.09)',  'rgba(0,31,63,.09)'),
    ('rgba(37,99,235,.10)',  'rgba(0,31,63,.10)'),
    ('rgba(37,99,235,.12)',  'rgba(0,31,63,.12)'),
    ('rgba(37,99,235,.13)',  'rgba(0,31,63,.13)'),
    ('rgba(37,99,235,.14)',  'rgba(0,31,63,.14)'),
    ('rgba(37,99,235,.15)',  'rgba(0,31,63,.15)'),
    ('rgba(37,99,235,.18)',  'rgba(0,31,63,.18)'),
    ('rgba(37,99,235,.22)',  'rgba(0,31,63,.22)'),
    ('rgba(37,99,235,.25)',  'rgba(0,31,63,.25)'),
    ('rgba(37,99,235,.45)',  'rgba(0,31,63,.45)'),

    # Direct solid blue primaries
    ('#2563eb', '#001F3F'),
    ('#1d4ed8', '#001F3F'),
    ('#1e3a8a', '#001F3F'),
    ('#1e40af', '#001F3F'),
    ('#1464cc', '#001F3F'),
    ('#1a47cc', '#001F3F'),
    ('#1877f2', '#001F3F'),
    ('#172554', '#001F3F'),

    # Lighter / mid blues -> tinted navy equivalents
    ('#3b82f6', '#4A7FA5'),
    ('#60a5fa', '#6B9EBD'),
    ('#93c5fd', '#8FBDD6'),
    ('#dbeafe', '#D6E4F0'),
    ('#bfdbfe', '#B8D4E8'),
    ('#eff6ff', '#EEF4FA'),
    ('#f0f4ff', '#EEF4FA'),

    # CTA section gradient backgrounds
    ('linear-gradient(135deg, #1a47cc 0%, #2563eb 50%, #1d4ed8 100%)',
     'linear-gradient(135deg, #001F3F 0%, #00305F 50%, #001F3F 100%)'),

    # Button primary color change  (btn-primary -> gold #C5952E)
    # We'll handle btn-primary after the blue replacements so var(--blue) is still in place
    # Actually we need to change the btn-primary BACKGROUND specifically
    # Let's change it using the var(--blue) that now points to #001F3F — leave it as var(--blue)
    # and separately override btn-primary to gold
    # We inject an override just for btn-primary after the var(--blue) chain is set
]

files_changed = []
for fname in sorted(os.listdir(css_dir)):
    if not fname.endswith('.css'):
        continue
    path = os.path.join(css_dir, fname)
    with open(path, encoding='utf-8') as f:
        content = f.read()
    original = content
    for old, new in replacements:
        content = content.replace(old, new)
    if content != original:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        files_changed.append(fname)

print('Done. Changed files:', files_changed)
