import base64
import math
import re

PATTERNS = {
    "aws_access_key_id": r"AKIA[0-9A-Z]{16}",
    "github_token": r"ghp_[A-Za-z0-9]{36}",
    "slack_token": r"xox[baprs]-[0-9A-Za-z-]{10,}",
    "huggingface_token": r"hf_[A-Za-z0-9]{30,}",
    "openai_key": r"sk-[A-Za-z0-9]{20,}",
    "private_key": r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    "jwt": r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+",
    "http_auth_header": r"(?i)authorization\s*:\s*(?:basic|bearer)\s+[A-Za-z0-9._/+=-]+",
    "generic_password": r"(?i)(?:password|passwd|pwd)\s*[=:]\s*\S{6,}",
    "generic_secret": r"(?i)(?:secret|api[_-]?key)\w*\s*[=:]\s*['\"]?[A-Za-z0-9/+_-]{16,}",
}

_COMPILED = {name: re.compile(p) for name, p in PATTERNS.items()}

HIGH_CONFIDENCE = {
    "aws_access_key_id", "github_token", "slack_token", "huggingface_token",
    "openai_key", "private_key", "jwt", "http_auth_header",
}


def _confidence(name):
    if name in HIGH_CONFIDENCE:
        return "high"
    if name.startswith("generic"):
        return "medium"
    return "low"


def _find(text):
    found = []
    for name, rx in _COMPILED.items():
        for m in rx.finditer(text):
            found.append({"type": name, "match": m.group(0), "confidence": _confidence(name)})
    return found


def _base64_decoded_parts(text):
    for token in re.findall(r"[A-Za-z0-9+/]{16,}={0,2}", text):
        try:
            decoded = base64.b64decode(token, validate=True).decode("utf-8")
        except Exception:
            continue
        if decoded.isprintable():
            yield decoded


def _shannon_entropy(s):
    counts = {}
    for c in s:
        counts[c] = counts.get(c, 0) + 1
    return -sum((n / len(s)) * math.log2(n / len(s)) for n in counts.values())


def _high_entropy_strings(text, min_len=24, threshold=4.3):
    for token in re.findall(r"[A-Za-z0-9+/_-]{%d,}" % min_len, text):
        if _shannon_entropy(token) >= threshold:
            yield token


def scan_text(text):
    findings = _find(text)
    for decoded in _base64_decoded_parts(text):
        for f in _find(decoded):
            f["type"] += "+base64"
            findings.append(f)

    already = {f["match"] for f in findings}
    for token in _high_entropy_strings(text):
        if token in already or any(token in m for m in already):
            continue
        findings.append({"type": "high_entropy", "match": token, "confidence": "low"})

    # Flag : tout ce qui n'est pas "high" mérite une vérification humaine.
    for f in findings:
        f["needs_review"] = f["confidence"] != "high"
    return findings