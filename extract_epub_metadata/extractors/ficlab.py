"""Explicit metadata in FicLab-marked EPUB front matter.

Summary story counts take precedence over OPF extent. ISO dates preserve their
offsets; displayed English dates are fallbacks. Mixed tags remain uncategorized.
"""
import datetime
import re

from ._epubxml import find_all, find_first, local_name, parse_opf, parse_xhtml, spine_item_paths, text_content
from ._numbers import parse_count


_PROFILE = re.compile(r'^https?://(?:www\.)?fanfiction\.net/u/(\d+)(?:/[^\s?#]*)?/?$', re.I)
_EXTENT = re.compile(r'^([\d,\s]+)\s+words$', re.I)
_DISPLAY_DATE = re.compile(r'^([A-Za-z]+) (\d{1,2})(?:st|nd|rd|th)?, (\d{4})$')
_MONTHS = {name.lower(): i for i, name in enumerate((
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'), 1)}


def _unique(values):
    values = set(v.strip() for v in values if v.strip())
    return next(iter(values)) if len(values) == 1 else None


def _timestamp(value):
    if not value:
        return None
    try:
        return datetime.datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        return None


def _display_date(value):
    match = _DISPLAY_DATE.fullmatch(value or '')
    if match is None or match[1].lower() not in _MONTHS:
        return None
    try:
        return datetime.date(int(match[3]), _MONTHS[match[1].lower()], int(match[2]))
    except ValueError:
        return None


def extract_ficlab(zf):
    """Return (fields, per-field sources), or empty dictionaries for other EPUBs."""
    root, opf_path = parse_opf(zf)
    if root is None:
        return {}, {}
    metadata = find_first(root, 'metadata')
    if metadata is None:
        return {}, {}
    identifiers = [text_content(e).strip() for e in find_all(metadata, 'identifier')]
    if 'META-INF/ficlab-id' not in zf.namelist() and not any(v.startswith('ficlab:') for v in identifiers):
        return {}, {}

    summary_values, author_links = {}, []
    for path in spine_item_paths(zf, root, opf_path)[:12]:
        page = parse_xhtml(zf, path)
        body = find_first(page, 'body') if page is not None else None
        if body is None:
            continue
        classes = (body.get('class') or '').split()
        if 'fl-summary' in classes:
            for row in find_all(body, 'tr'):
                cells = [e for e in row if local_name(e.tag) in ('th', 'td')]
                if len(cells) != 2:
                    continue
                label = ' '.join(text_content(cells[0]).split()).lower()
                value = ' '.join(text_content(cells[1]).split())
                if label and value:
                    summary_values.setdefault(label, []).append(value)
        if 'fl-copyright' in classes:
            for paragraph in find_all(body, 'p'):
                if 'copyrighted by' not in text_content(paragraph).lower():
                    continue
                for link in find_all(paragraph, 'a'):
                    url = (link.get('href') or '').strip()
                    match = _PROFILE.fullmatch(url)
                    name = text_content(link).strip()
                    if match and name and (name, url, match[1]) not in author_links:
                        author_links.append((name, url, match[1]))

    summary = {key: _unique(values) for key, values in summary_values.items()}
    properties = {}
    for meta in find_all(metadata, 'meta'):
        if meta.get('property'):
            properties.setdefault(meta.get('property'), []).append(text_content(meta).strip())
    fields, sources = {}, {}

    def put(key, value, source):
        if value not in (None, '', []):
            fields[key], sources[key] = value, source

    for label, key in (('title', 'title'), ('rating', 'rating'), ('source', 'storyUrl')):
        put(key, summary.get(label), 'ficlab_summary')
    status = {'complete': 'Completed', 'completed': 'Completed',
              'in-progress': 'In-Progress', 'in progress': 'In-Progress',
              'incomplete': 'In-Progress', 'ongoing': 'In-Progress'}.get((summary.get('status') or '').lower())
    put('status', status, 'ficlab_summary')
    put('numChapters', parse_count(summary.get('chapters')), 'ficlab_summary')
    if 'words' in summary_values:
        # An invalid/conflicting stated count is not silently replaced by an
        # unrelated extent. Only absence permits the fallback.
        put('numWords', parse_count(summary.get('words')), 'ficlab_summary')
    else:
        extent = _EXTENT.fullmatch(_unique(properties.get('dcterms:extent', [])) or '')
        if extent:
            put('numWords', parse_count(extent[1]), 'ficlab_opf')

    subjects = [text_content(e).strip() for e in find_all(metadata, 'subject') if text_content(e).strip()]
    if subjects:
        # Separate subject elements preserve tag boundaries even when a tag
        # contains a comma. The displayed comma-separated list is a fallback.
        put('extratags', subjects, 'ficlab_opf')
    elif 'tags' in summary_values:
        tags = [tag.strip() for tag in (summary.get('tags') or '').split(',') if tag.strip()]
        put('extratags', tags, 'ficlab_summary')

    for key, prop_names, label in (
        ('datePublished', ('dcterms:issued', 'dcterms:date'), 'published'),
        ('dateUpdated', ('dcterms:modified',), 'updated'),
    ):
        date = None
        for prop in prop_names:
            date = _timestamp(_unique(properties.get(prop, [])))
            if date is not None:
                break
        if date is None and key == 'datePublished':
            date = _timestamp(_unique([text_content(e) for e in find_all(metadata, 'date')]))
        if date is not None:
            put(key, date, 'ficlab_opf')
        else:
            put(key, _display_date(summary.get(label)), 'ficlab_summary')

    authors = [text_content(e).strip() for e in find_all(metadata, 'creator') if text_content(e).strip()]
    # Match explicit profiles to the actual authors; unrelated copyright links
    # must not become author identifiers, or be assigned in an arbitrary order.
    profiles = []
    for name in authors:
        matches = [item for item in author_links if item[0].casefold() == name.casefold()]
        if len(matches) != 1:
            profiles = []
            break
        profiles.append(matches[0])
    if profiles:
        put('authorUrl', [item[1] for item in profiles], 'ficlab_copyright')
        put('authorId', [item[2] for item in profiles], 'ficlab_copyright')
    return fields, sources
