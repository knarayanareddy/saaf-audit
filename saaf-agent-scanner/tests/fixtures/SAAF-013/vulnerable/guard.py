import re

PATTERNS = [
    ("hidden-markup", r"<!--(?:(?!-->)[\s\S])*?[A-Za-z]{2,}(?:(?!-->)[\s\S])*?-->"),
]
STRIP = re.compile(r"<[^>]*.*?-->")
NESTED = re.compile(r"^(a+)+$")
LAZY = re.compile(r"(\s|.)*?END")
COMPILED = [(n, re.compile(p)) for n, p in PATTERNS]
