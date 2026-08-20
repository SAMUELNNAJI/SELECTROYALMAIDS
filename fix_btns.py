import os

path = 'static/css/style.css'
with open(path, encoding='utf-8') as f:
    content = f.read()

# mc-btn--primary -> gold
old = (
    '.mc-btn--primary {\n'
    '  background: var(--blue);\n'
    '  color: #fff;\n'
    '  border-color: var(--blue);\n'
    '}\n'
    '.mc-btn--primary:hover {\n'
    '  background: var(--blue-dark);\n'
    '  border-color: var(--blue-dark);\n'
    '}'
)
new = (
    '.mc-btn--primary {\n'
    '  background: #C5952E;\n'
    '  color: #fff;\n'
    '  border-color: #C5952E;\n'
    '}\n'
    '.mc-btn--primary:hover {\n'
    '  background: #A87A22;\n'
    '  border-color: #A87A22;\n'
    '}'
)
content = content.replace(old, new)

# mobile nav btn-primary -> gold
old2 = (
    '  .nav-links.open .mobile-nav-cta .btn-primary {\n'
    '    background: var(--blue);\n'
    '    color: #fff;\n'
    '    padding: 14px 20px;\n'
    '    border-radius: 100px;\n'
    '  }'
)
new2 = (
    '  .nav-links.open .mobile-nav-cta .btn-primary {\n'
    '    background: #C5952E;\n'
    '    color: #fff;\n'
    '    padding: 14px 20px;\n'
    '    border-radius: 100px;\n'
    '  }'
)
content = content.replace(old2, new2)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print('done')
