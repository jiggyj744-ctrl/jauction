import os, glob

docs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'docs')
count = 0
for f in glob.glob(os.path.join(docs_dir, 'auction', '*.html')):
    with open(f, 'r', encoding='utf-8') as fh:
        content = fh.read()
    if 'onerror' not in content:
        content = content.replace(
            ' loading="lazy">',
            " loading=\"lazy\" onerror=\"this.style.display='none'\">"
        )
        with open(f, 'w', encoding='utf-8') as fh:
            fh.write(content)
        count += 1
print(f'Updated {count} files')