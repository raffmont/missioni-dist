"""Fail on forbidden binary documents or common personal-data patterns."""
from pathlib import Path
import re
import subprocess
import sys

tracked = subprocess.check_output(["git", "ls-files", "-co", "--exclude-standard"], text=True).splitlines()
forbidden_ext = {".pdf", ".docx", ".xlsx", ".xls", ".p12", ".pfx", ".pem", ".key", ".sql"}
patterns = {
    "non-example email": re.compile(r"[\w.+-]+@(?!example\.org\b)[\w.-]+\.[A-Za-z]{2,}"),
    "Italian fiscal code": re.compile(r"\b[A-Z]{6}[0-9]{2}[A-EHLMPRST][0-9]{2}[A-Z][0-9]{3}[A-Z]\b", re.I),
    "IBAN": re.compile(r"\bIT\d{2}[A-Z]\d{10}[A-Z0-9]{12}\b", re.I),
}
errors = []
for name in tracked:
    path = Path(name)
    if path.suffix.lower() in forbidden_ext:
        errors.append(f"forbidden file type: {name}")
        continue
    try:
        content = path.read_text(errors="ignore")
    except OSError:
        continue
    for label, pattern in patterns.items():
        if pattern.search(content):
            errors.append(f"{label}: {name}")
if errors:
    print("Public repository guard failed:\n" + "\n".join(errors), file=sys.stderr)
    raise SystemExit(1)
print("Public repository guard passed (synthetic data only).")
