"""Conservative labelled headers in PDF-reflow EPUBs, without AO3 markup.

Only a short opening header is read, and only in a document explicitly
marked as a PDF conversion. Freehand fandoms/pairings/warnings stay intact;
their commas are not assumed to be structured tag separators.
"""
import re
from urllib.parse import urlsplit

from ._epubxml import find_all, parse_opf, parse_xhtml, spine_item_paths
from ._numbers import parse_count
from .ao3_pdf_preface import _lines

_LABEL = re.compile(r'^([A-Za-z][A-Za-z /-]{0,30}):\s*(.+)$')
_KEYS = {
    'title': 'title', 'rating': 'rating', 'fandom': 'fandoms',
    'pairing': 'ships', 'relationship': 'ships', 'warnings': 'warnings',
    'word count': 'numWords',
}
_LIST_KEYS = {'fandoms', 'ships', 'warnings'}


def _original_livejournal_url(lines):
    # The archive's explicit "Original" notice identifies the source post.
    # Do not mistake links to fanart, profiles, or other cited works for it.
    for text, elem in lines:
        if not re.search(r'\b(?:original|оригинал)\s*:', text, re.I):
            continue
        for a in find_all(elem, 'a'):
            href = (a.get('href') or '').strip()
            try:
                parsed = urlsplit(href)
            except ValueError:
                continue
            if (parsed.scheme in ('http', 'https') and
                    re.fullmatch(r'[a-z0-9_-]+\.livejournal\.com', parsed.netloc, re.I) and
                    re.fullmatch(r'/[0-9]+\.html', parsed.path)):
                return href
    return None


def extract_pdf_header(zf):
    root, path = parse_opf(zf)
    if root is None:
        return None
    # Covers can precede the converted document, but do not scan later
    # chapter files for prose that happens to resemble metadata.
    for item in spine_item_paths(zf, root, path)[:3]:
        page = parse_xhtml(zf, item)
        if page is None:
            continue
        generators = [e.get('content', '').lower() for e in find_all(page, 'meta')
                      if e.get('name', '').lower() == 'generator']
        if not any('pdf' in g and ('conversion' in g or 'reflow' in g) for g in generators):
            continue
        lines = _lines(page)[:40]
        entries, start = {}, None
        for index, (text, _elem) in enumerate(lines):
            match = _LABEL.fullmatch(text)
            label = match.group(1).lower() if match else None
            if start is None:
                if label != 'title':
                    continue
                start = index
            if label not in _KEYS:
                break  # author notes, blanks, and story prose end the header
            entries.setdefault(label, match.group(2).strip())
        # Several explicit labels distinguish metadata from ordinary text.
        if 'title' not in entries or 'rating' not in entries or not any(
                k in entries for k in ('fandom', 'pairing', 'relationship')):
            return None
        result = {}
        for label, value in entries.items():
            key = _KEYS[label]
            if key == 'numWords':
                value = parse_count(value)  # "~3400" is not an exact count
                if value is None:
                    continue
            result.setdefault(key, [value] if key in _LIST_KEYS else value)
        original = _original_livejournal_url(lines[:start])
        if original:
            result['storyUrl'] = original
        return result
    return None
