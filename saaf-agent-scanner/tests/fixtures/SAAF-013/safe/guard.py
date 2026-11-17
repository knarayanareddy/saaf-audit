import re

MAX_DOC = 200_000
PATTERNS = [
    ("hidden-markup", r"<!--[^>]{0,2000}-->"),
]
STRIP = re.compile(r"<[^>]{0,200}>")
EMAIL = re.compile(r"[a-z0-9._%+-]{1,64}@[a-z0-9.-]{1,255}\.[a-z]{2,}")


def has_marker(text: str) -> bool:
    start = text.find("<!--")
    return start != -1 and text.find("-->", start) != -1
