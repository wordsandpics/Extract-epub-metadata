"""Strict counts from EPUB metadata; never concatenate separate numbers."""
import re

COUNT_PATTERN = r'[0-9]+(?:,[0-9]{3}|[ \u00a0\u2007\u2009\u202f][0-9]{3})*'


def parse_count(value):
    if isinstance(value, int) and not isinstance(value, bool):
        return value if value >= 0 else None
    text = str(value).strip() if value is not None else ''
    if not re.fullmatch(COUNT_PATTERN, text):
        return None
    return int(re.sub(r'[, \u00a0\u2007\u2009\u202f]', '', text))
