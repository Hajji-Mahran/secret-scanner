import hashlib
import os
import subprocess


def _is_text(data):
    """Heuristique simple : un octet nul => binaire."""
    return b"\x00" not in data


def _decode(data):
    return data.decode("utf-8", errors="replace")


def walk_working_tree(repo):
    for root, dirs, files in os.walk(repo):
        if ".git" in dirs:
            dirs.remove(".git")  # ne pas descendre dans .git
        for name in files:
            full = os.path.join(root, name)
            try:
                with open(full, "rb") as f:
                    data = f.read()
            except OSError:
                continue
            if not _is_text(data):
                continue
            yield {
                "source": "worktree",
                "ref": os.path.relpath(full, repo),
                "content": _decode(data),
            }


def all_git_objects(repo):
    listing = subprocess.run(
        ["git", "-C", repo, "cat-file", "--batch-all-objects", "--batch-check"],
        capture_output=True, text=True,
    )
    for line in listing.stdout.splitlines():
        parts = line.split()
        if len(parts) != 3:
            continue
        sha, obj_type, _size = parts
        if obj_type != "blob":
            continue
        blob = subprocess.run(
            ["git", "-C", repo, "cat-file", "blob", sha],
            capture_output=True,  # bytes (pas de text=True)
        )
        if not _is_text(blob.stdout):
            continue
        yield {"source": "object", "ref": sha, "content": _decode(blob.stdout)}


def collect_items(repo):
    seen = set()
    items = []
    for item in list(walk_working_tree(repo)) + list(all_git_objects(repo)):
        digest = hashlib.sha1(item["content"].encode("utf-8", "replace")).hexdigest()
        if digest in seen:
            continue
        seen.add(digest)
        items.append(item)
    return items