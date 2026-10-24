import os
import re
from pathlib import Path

suspicious_patterns = [
    re.compile(r'if\s+["\']test["\']\s+in', re.I),
    re.compile(r'if\s+is_test', re.I),
    re.compile(r'return\s+["\']dummy["\']', re.I),
    re.compile(r'return\s+\{\s*["\']ok["\']:\s*True\s*\}\s*#\s*mock', re.I),
    re.compile(r'#\s*hardcoded\s+for\s+test', re.I),
    re.compile(r'#\s*bypass', re.I),
]

dirs_to_check = ['services', 'documentary', 'vendor/media_factory/backend/app']
found = []
for d in dirs_to_check:
    for root, _, files in os.walk(d):
        for f in files:
            if f.endswith('.py'):
                p = Path(root) / f
                try:
                    text = p.read_text(encoding='utf-8', errors='ignore')
                    for line_no, line in enumerate(text.splitlines(), 1):
                        for pat in suspicious_patterns:
                            if pat.search(line):
                                found.append((str(p), line_no, line.strip()))
                except Exception:
                    pass

print(f"Total suspicious hits in production code: {len(found)}")
for p, lno, l in found:
    print(f"{p}:{lno} -> {l}")
