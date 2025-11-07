#!/usr/bin/env python3
import subprocess
from pathlib import Path
import re

exts = ('.py','.md','.txt','.yaml','.yml','.json','.html','.xml','.cfg','.ini','.sh','.bat','.csv','.toml')
root = Path('.')
files = [p for p in (subprocess.check_output(['git','ls-files']).decode().splitlines()) if p.endswith(exts)]
changed = []
for f in files:
    p = Path(f)
    try:
        s = p.read_text(encoding='utf-8')
    except Exception:
        continue
    # normalize line endings and strip trailing whitespace
    lines = re.sub(r"\r\n|\r|\n", "\n", s).split('\n')
    fixed_lines = [re.sub(r'[ \t]+$', '', L) for L in lines]
    out = '\n'.join(fixed_lines)
    if not out.endswith('\n'):
        out = out + '\n'
    if out != s:
        p.write_text(out, encoding='utf-8')
        changed.append(f)

if changed:
    print('Modified files:')
    for c in changed:
        print(c)
    subprocess.run(['git','add'] + changed, check=False)
    subprocess.run(['git','commit','-m','chore: apply pre-commit auto-fixes (trim trailing whitespace, ensure newline EOF)'], check=False)
    subprocess.run(['git','push','origin','chore/fix-warnings'], check=False)
else:
    print('No files modified')
