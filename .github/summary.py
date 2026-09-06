"""Writes what a workflow job did into the summary of its run.

Reads what the tools left behind and prints markdown, which the workflow appends to
GITHUB_STEP_SUMMARY. Exits non-zero only when asked about jobs that did not pass.
"""
import json
import os
import sys
import xml.etree.ElementTree as ET

passing = ("success", "skipped")
marks = {"success": "✅", "skipped": "⏭️"}
limit = 10


def shorten(text: str, length: int = 90) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= length else text[:length - 1] + "…"


def tests(path: str) -> int:
    root = ET.parse(path).getroot()
    suite = root.find("testsuite")
    if suite is None:
        suite = root
    total = int(suite.get("tests", 0))
    failures = int(suite.get("failures", 0)) + int(suite.get("errors", 0))
    skipped = int(suite.get("skipped", 0))
    print("## Tests\n")
    print("| Ran | Passed | Failed | Skipped | Time |")
    print("| --- | --- | --- | --- | --- |")
    print("| " + " | ".join([str(total), str(total - failures - skipped),
                             str(failures), str(skipped),
                             "{:.0f} s".format(float(suite.get("time", 0)))]) + " |")
    broken = [case for case in suite.iter("testcase")
              if case.find("failure") is not None or case.find("error") is not None]
    if not broken:
        print("\nEvery test passed. ✅")
        return 0
    print("\n### What failed\n")
    print("| Test | Why |")
    print("| --- | --- |")
    for case in broken[:limit]:
        problem = case.find("failure")
        if problem is None:
            problem = case.find("error")
        where = case.get("classname", "") + "." + case.get("name", "")
        print("| `" + where + "` | " + shorten(problem.get("message", "")) + " |")
    if len(broken) > limit:
        print("\nAnd " + str(len(broken) - limit) + " more.")
    return 0


def counted(number: int, one: str, many: str) -> str:
    return str(number) + " " + (one if number == 1 else many)


def audit(path: str) -> int:
    if not os.path.isfile(path):
        print("## Vulnerable dependencies\n")
        print("The audit left no result behind, so it did not get to run. ❌")
        return 0
    with open(path, encoding='utf8') as f:
        found = json.load(f)
    packages = found.get("dependencies", [])
    risky = [(one, vuln) for one in packages for vuln in one.get("vulns", [])]
    print("## Vulnerable dependencies\n")
    if not risky:
        print("No known vulnerabilities found in " + counted(len(packages), "package", "packages") + ". ✅")
        return 0
    print("| Package | Version | Advisory | Also known as | Fixed in |")
    print("| --- | --- | --- | --- | --- |")
    for one, vuln in risky:
        names = ", ".join(vuln.get("aliases") or []) or "-"
        fixes = ", ".join(vuln.get("fix_versions") or []) or "no fix yet"
        print("| " + " | ".join([one.get("name", "?"), one.get("version", "?"),
                                 vuln.get("id", "?"), names, fixes]) + " |")
    packages_hit = len({one.get("name") for one, _ in risky})
    print("\n" + counted(len(risky), "advisory", "advisories") + " in " +
          counted(packages_hit, "package", "packages") + ". ❌")
    return 0


def jobs(pairs: list[str]) -> int:
    print("## Jobs summary\n")
    print("| Job | Result |")
    print("| --- | --- |")
    failed = []
    for pair in pairs:
        name, _, result = pair.partition("=")
        is_fine = result in passing
        print("| " + name + " | " + marks.get(result, "❌") + " " + (result or "missing") + " |")
        if not is_fine:
            failed.append(name)
    if failed:
        print("\nDid not pass: " + ", ".join(failed) + ".")
        return 1
    print("\nEverything passed.")
    return 0


def main() -> int:
    what, arguments = sys.argv[1], sys.argv[2:]
    if what == "tests":
        return tests(arguments[0])
    if what == "audit":
        return audit(arguments[0])
    if what == "jobs":
        return jobs(arguments)
    raise SystemExit("Unknown summary: " + what)


if __name__ == "__main__":
    sys.exit(main())
