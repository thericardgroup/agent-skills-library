#!/usr/bin/env python3
"""Check and fix the environment before the user is asked to care about it.

A first-time Claude Code user should never see a dependency error. Run this at the
start of a session; it reports what is ready and what it fixed. Only surface
something to the user if it genuinely cannot be resolved here.
"""
import json, os, shutil, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from statepath import state_root, FILES

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCGEN = os.path.join(SKILL_DIR, "scripts", "docgen")

def have(cmd): return shutil.which(cmd) is not None

def main():
    report = {"ready": True, "fixed": [], "blocked": [], "state": {}}

    if sys.version_info < (3, 8):
        report["blocked"].append("Python 3.8+ required (only the standard library is used).")
        report["ready"] = False

    root = state_root()
    report["state_root"] = root
    for f in FILES:
        report["state"][f] = "present" if os.path.exists(os.path.join(root, f)) else "not yet"

    # Document generation is optional until the user actually packages something,
    # so a missing Node is a note, not a blocker.
    if not have("node") or not have("npm"):
        report["blocked"].append(
            "Node is not installed. Everything works except generating resume and "
            "cover letter files. Install Node from nodejs.org when you get to that step."
        )
    else:
        if not os.path.isdir(os.path.join(DOCGEN, "node_modules")):
            try:
                subprocess.run(["npm", "install", "docx", "jszip", "--silent",
                                "--no-audit", "--no-fund"],
                               cwd=DOCGEN, check=True, capture_output=True, timeout=180)
                report["fixed"].append("Installed document-generation libraries.")
            except Exception:
                report["blocked"].append(
                    "Could not install document libraries automatically. "
                    f"Run: npm --prefix {DOCGEN} install docx jszip"
                )

    # PDF export is a nicety and macOS-only. Never block on it.
    report["pdf_available"] = sys.platform == "darwin" and os.path.isdir(
        "/Applications/Microsoft Word.app")

    print(json.dumps(report, indent=1))
    return 0 if report["ready"] else 1

if __name__ == "__main__":
    sys.exit(main())
