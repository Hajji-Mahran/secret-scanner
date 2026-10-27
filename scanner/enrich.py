import subprocess


def _run(repo, args):
    return subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True).stdout


def _all_commits(repo):
    commits = set(_run(repo, ["rev-list", "--all", "--reflog"]).split())
    for line in _run(repo, ["fsck", "--unreachable"]).splitlines():
        parts = line.split()
        if len(parts) == 3 and parts[1] == "commit":
            commits.add(parts[2])  # orphelins (ex. stash droppé)
    return commits


def _meta(repo, commit):
    out = _run(repo, ["show", "-s", "--format=%an <%ae>|%aI", commit]).strip()
    author, _, date = out.partition("|")
    return author, date


def build_index(repo):
    """blob_sha -> {path, commit, author, date}."""
    index = {}
    for commit in _all_commits(repo):
        author, date = _meta(repo, commit)
        for line in _run(repo, ["ls-tree", "-r", commit]).splitlines():
            meta, _, path = line.partition("\t")      # "<mode> blob <sha>\t<path>"
            parts = meta.split()
            if len(parts) == 3 and parts[1] == "blob":
                index.setdefault(parts[2], {
                    "path": path, "commit": commit, "author": author, "date": date,
                })
    return index


def locate(repo, index, item):
    """Localisation d'un élément (blob objet ou fichier worktree)."""
    ref, source = item["ref"], item["source"]
    if source == "object":
        return index.get(ref, {"path": None, "commit": None, "author": None, "date": None})
    # worktree : on tente le dernier commit touchant ce chemin
    meta = _run(repo, ["log", "-1", "--format=%an <%ae>|%aI", "--", ref]).strip()
    if meta:
        author, _, date = meta.partition("|")
        return {"path": ref, "commit": None, "author": author, "date": date}
    return {"path": ref, "commit": None, "author": None, "date": None}
