import json


def _redact(secret):
    s = secret.strip()
    if len(s) <= 12:
        return s[:2] + "***"
    return f"{s[:4]}...{s[-4:]}"


def build(findings, redact=False):
    out = []
    for f in findings:
        out.append({
            "type": f["type"],
            "secret": _redact(f["match"]) if redact else f["match"],
            "confidence": f["confidence"],
            "needs_review": f["needs_review"],
            "source": f["source"],
            "path": f["path"],
            "commit": f["commit"],
            "author": f["author"],
            "date": f["date"],
        })
    return out


def to_json(findings, pretty=False, redact=False):
    data = build(findings, redact=redact)
    return json.dumps(data, indent=2 if pretty else None, ensure_ascii=False)