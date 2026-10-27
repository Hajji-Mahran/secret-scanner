#!/usr/bin/env python3
import argparse
import os
import subprocess
import sys

from scanner import collect, detect, enrich, report


def is_git_repo(path):
    result = subprocess.run(
        ["git", "-C", path, "rev-parse", "--git-dir"],
        capture_output=True, text=True,
    )
    return result.returncode == 0


def scan(repo):
    items = collect.collect_items(repo)
    index = enrich.build_index(repo)

    seen, findings = set(), []
    for item in items:
        for f in detect.scan_text(item["content"]):
            key = (item["ref"], f["match"])
            if key in seen:
                continue
            seen.add(key)
            loc = enrich.locate(repo, index, item)
            findings.append({**f, "source": item["source"], **loc})
    return findings


def main():
    parser = argparse.ArgumentParser(description="Trouve les secrets récupérables dans un dépôt Git.")
    parser.add_argument("repo", help="Chemin du dépôt Git à scanner")
    parser.add_argument("--pretty", action="store_true", help="JSON indenté")
    parser.add_argument("--redact", action="store_true", help="Masque la valeur des secrets")
    args = parser.parse_args()

    if not os.path.isdir(args.repo) or not is_git_repo(args.repo):
        print(f"erreur : '{args.repo}' n'est pas un dépôt Git", file=sys.stderr)
        sys.exit(1)

    findings = scan(args.repo)
    print(report.to_json(findings, pretty=args.pretty, redact=args.redact))


if __name__ == "__main__":
    main()