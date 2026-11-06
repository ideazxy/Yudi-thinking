"""Prepare isolated skill comparisons and check their file side effects."""

import argparse
import json
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CASES = {
    case["id"]: case
    for case in json.loads((ROOT / "evals/cases.json").read_text(encoding="utf-8"))
}


def git(work, *args):
    return subprocess.check_output(["git", "-C", str(work), *args]).decode("utf-8")


def install_runtime(source, work):
    target = work / ".agents/skills/yudi-thinking"
    target.mkdir(parents=True)
    shutil.copy2(source / "SKILL.md", target)
    for name in ("references", "agents"):
        shutil.copytree(source / name, target / name)


def prepare(args):
    old, out = args.old.resolve(), args.out.resolve()
    groups = {"bare": None, "previous": old, "candidate": ROOT}
    if not (old / "SKILL.md").is_file():
        raise SystemExit(f"Missing old skill at {old}")
    if out.is_relative_to(ROOT) or out.is_relative_to(old):
        raise SystemExit("Choose an output directory outside both skill checkouts.")
    out.mkdir(parents=True, exist_ok=False)
    case_ids = list(dict.fromkeys(args.case or CASES))
    for case_id in case_ids:
        case = CASES[case_id]
        for group, source in groups.items():
            trial = out / case_id / group
            work = trial / "work"
            work.mkdir(parents=True)
            git(work, "init", "-q")
            for name, content in case["files"].items():
                (work / name).write_text(content, encoding="utf-8")
            if source is not None:
                install_runtime(source, work)
            git(work, "add", "-f", "--", ".")
            (trial / "initial-tree").write_text(git(work, "write-tree"), encoding="utf-8")
            (trial / "prompt.txt").write_text(case["prompt"] + "\n", encoding="utf-8")
    print(f"Prepared {len(case_ids) * len(groups)} workspaces in {out}")


def check_files(args):
    prompts = sorted(args.out.glob("*/*/prompt.txt"))
    if not prompts:
        raise SystemExit("No prepared trials in this directory.")
    failures = 0
    for prompt in prompts:
        trial = prompt.parent
        work = trial / "work"
        label = trial.relative_to(args.out)
        answer = trial / "answer.md"
        if not answer.is_file() or not answer.read_text(encoding="utf-8").strip():
            print(f"UNRUN {label} (no answer)")
            failures += 1
            continue
        initial = (trial / "initial-tree").read_text(encoding="utf-8").strip()
        tracked = git(work, "diff", "--no-renames", "--name-only", "-z", initial, "--")
        untracked = git(work, "ls-files", "--others", "-z")
        changed = sorted(set(filter(None, (tracked + untracked).split("\0"))))
        expected = sorted(CASES[trial.parent.name].get("expected_changes", []))
        passed = changed == expected
        print(f"{'PASS' if passed else 'FAIL'} {label} changed={changed} expected={expected}")
        if not passed:
            failures += 1
    return int(failures > 0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    setup = commands.add_parser("prepare")
    setup.add_argument("--old", required=True, type=Path, help="Previous skill checkout")
    setup.add_argument("--out", required=True, type=Path, help="New comparison directory")
    setup.add_argument("--case", action="append", choices=CASES, help="Limit cases; repeatable")
    check = commands.add_parser("check-files")
    check.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    if args.command == "prepare":
        return prepare(args)
    return check_files(args)


if __name__ == "__main__":
    raise SystemExit(main())
