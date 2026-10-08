#!/usr/bin/env python3
"""Check that the shared layout contract is identical in both skills.

Each SKILL.md carries the contract between `<!-- contract:start ... -->` and
`<!-- contract:end -->`. The skills are installed standalone, so each needs its
own copy; this fails (exit 1) when the copies drift apart.

    python tools/check_contract.py          # compare
    python tools/check_contract.py --sync   # copy the planner's block into the reporter
"""
import difflib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = [ROOT / "skills" / name / "SKILL.md"
          for name in ("ml-experiment-planner", "ml-experiment-reporter")]
BLOCK = re.compile(r"<!-- contract:start.*?-->\n(.*?)<!-- contract:end -->", re.S)


def block(path):
    m = BLOCK.search(path.read_text())
    if not m:
        sys.exit(f"error: no contract block in {path.relative_to(ROOT)}")
    return m


def main():
    planner, reporter = (block(p) for p in SKILLS)
    if planner.group(1) == reporter.group(1):
        print("contract blocks match")
        return
    if "--sync" in sys.argv:
        text = SKILLS[1].read_text()
        SKILLS[1].write_text(text[:reporter.start(1)] + planner.group(1) + text[reporter.end(1):])
        print("reporter contract block replaced with the planner's")
        return
    sys.stdout.writelines(difflib.unified_diff(
        planner.group(1).splitlines(True), reporter.group(1).splitlines(True),
        *(str(p.relative_to(ROOT)) for p in SKILLS)))
    sys.exit(1)


if __name__ == "__main__":
    main()
