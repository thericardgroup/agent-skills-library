#!/usr/bin/env python3
"""Fail if anything in this repository looks like one person's data.

Runs across every plugin, because the whole repository is published together and
a leak in one skill is a leak in all of them.

Detects SHAPES, never specific values, so this file stays safe to publish
alongside the skill it guards. Run before every release.
"""
import re, sys, os, json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP_DIRS = {"node_modules", ".git", ".handoffs", ".claude", "state", "tools", "evals"}
SKIP_FILES = {"package-lock.json"}

SHAPES = [
    ("phone number",      re.compile(r'\(?\b\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}\b')),
    ("email address",     re.compile(r'\b[\w.+-]+@[\w-]+\.[\w.]{2,}\b')),
    ("linkedin profile",  re.compile(r'linkedin\.com/in/[\w-]+')),
    ("street address",    re.compile(r'\b\d{1,5}\s+\w+(\s\w+)*\s(St|Street|Ave|Avenue|Rd|Road|Blvd|Dr|Drive|Ln|Lane)\b')),
    ("salary figure",     re.compile(r'\$\s?\d{2,3},\d{3}\b')),
    ("personal domain",   re.compile(r'https?://(www\.)?[\w-]+\.(com|io|co|net)/?(?![\w/])')),
]

# A literal collection of employer-like proper nouns is a personal applied-list,
# not configuration. Allowed only if the file reads it from the profile.
EMPLOYER_SET = re.compile(r'=\s*\{[^}]*(?:[\'"][a-z][\w&. ]{2,}[\'"]\s*,\s*){4,}[^}]*\}')

# Values reserved for documentation and fiction. Kept deliberately narrow: this
# is the one place a real detail could slip through, so it matches the actual
# reserved ranges rather than anything that merely looks like a sample.
#   555-0100..555-0199  reserved for fiction (NANP)
#   example.com/.org/.net, example.edu   reserved by RFC 2606
FICTIONAL = re.compile(
    r'555-01\d\d'
    r'|example\.(?:com|org|net|edu)'
    r'|/in/example\b'
    r'|REPLACE_ME|OWNER\b'
    r'|<[A-Za-z_]+>|\{\{|\$\{',
    re.I)

# Line-level exemption for code that reads the value from the profile at runtime.
ALLOW = re.compile(r'#\s*profile-sourced|//\s*profile-sourced', re.I)

def publisher_domains():
    """Domains the publisher declares as their own in the manifests.

    A publisher's website in their own README or plugin manifest is attribution,
    not a user's identity baked into shipped logic. Rather than exempt whole
    files, the allowance is tied to what the manifests actually declare, so it
    covers exactly the publisher and nothing else. Emails and phone numbers are
    never allowed anywhere, including here.
    """
    found = set()
    for rel in (".claude-plugin/marketplace.json",
                "plugins/*/.claude-plugin/plugin.json"):
        import glob
        for path in glob.glob(os.path.join(ROOT, rel)):
            try:
                raw = open(path, encoding="utf-8").read()
            except OSError:
                continue
            for m in re.finditer(
                    r'"(?:homepage|url|repository|documentation)"\s*:\s*"([^"]+)"', raw):
                host = re.sub(r'^https?://(www\.)?', '', m.group(1)).split('/')[0]
                if host:
                    found.add(host.lower())
    return found


PUBLISHER = publisher_domains()


def scan():
    hits = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if fn in SKIP_FILES or fn.startswith('.'):
                continue
            if not fn.endswith(('.py', '.js', '.md', '.json', '.ts')):
                continue
            path = os.path.join(dirpath, fn)
            rel = os.path.relpath(path, ROOT)
            try:
                lines = open(path, encoding='utf-8', errors='replace').read().splitlines()
            except Exception:
                continue
            for i, line in enumerate(lines, 1):
                if ALLOW.search(line):
                    continue
                for label, pat in SHAPES:
                    for m in pat.finditer(line):
                        # Judge the matched text, not the whole line: a real
                        # detail sitting beside a placeholder must still fail.
                        if FICTIONAL.search(m.group(0)):
                            continue
                        if label == "personal domain" and any(
                                d in m.group(0).lower() for d in PUBLISHER):
                            continue
                        hits.append((rel, i, f"{label}"))
                        break
                if EMPLOYER_SET.search(line):
                    hits.append((rel, i, "hardcoded employer/entity list"))
    return hits

if __name__ == "__main__":
    hits = scan()
    if not hits:
        print("PASS  no personal-data shapes found in shipped files")
        sys.exit(0)
    print(f"FAIL  {len(hits)} personal-data shape(s) in files that ship to users:\n")
    for rel, ln, label in hits:
        print(f"  {rel}:{ln}  {label}")
    print("\nEach must come from the user's profile at runtime, not a literal.")
    sys.exit(1)
