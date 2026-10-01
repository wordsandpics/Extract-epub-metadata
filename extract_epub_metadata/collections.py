"""Collection facts from outer OPF, embedded stories, or a saved series page.

Never run the single-story cascade for a collection. In particular, its
series URL is not a storyUrl and its first story is not the whole book.
"""
import re
from urllib.parse import urlsplit

from .anthology import extract_fic_records, is_anthology, _parse_date
from .extractors._epubxml import (
    find_all, local_name, parse_opf, parse_xhtml, spine_item_paths, text_content,
)
from .extractors._numbers import parse_count
from .extractors._urls import canonical_ao3_url, unwrap_wayback_url
from .extractors.opf import extract_opf


def primary_url(opf):
    for scheme in ('url', 'uri'):
        candidate = (opf.get('identifiers') or {}).get(scheme)
        if candidate and candidate.startswith(('http://', 'https://')):
            return candidate
    return opf.get('dc_source')


def extract_collection(zf, opf=None):
    """Return (fields, sources) or None for an ordinary story EPUB."""
    opf = extract_opf(zf) if opf is None else opf
    raw_url = primary_url(opf)
    url = unwrap_wayback_url(raw_url) or raw_url
    url = canonical_ao3_url(url) or url
    merged = is_anthology(zf)
    series_url = bool(url and re.fullmatch(r'/series/[0-9]+/?', urlsplit(url).path))
    if not merged and not series_url:
        return None

    fields = {'collectionType': 'epubmerge anthology' if merged else 'series collection'}
    for old, new in (('title', 'title'), ('authors', 'author'),
                     ('language', 'langcode'), ('description', 'description'),
                     ('subjects', 'collectionTags')):
        if opf.get(old):
            fields[new] = opf[old]
    if url:
        fields['collectionUrl'] = url
    if unwrap_wayback_url(raw_url):
        fields['waybackUrl'] = raw_url
    sources = {k: 'collection_opf' for k in fields}

    if merged:
        records = extract_fic_records(zf)
        fields['collectionRecords'] = records
        if records:
            fields['collectionStoryCount'] = len(records)
            fields['collectionUnknownCount'] = sum(
                r.get('status') not in ('Completed', 'In-Progress') for r in records)
            if fields['collectionUnknownCount'] < len(records):
                fields['collectionCompletedCount'] = sum(r.get('status') == 'Completed' for r in records)
            # A lost/unreadable title page must not yield a partial total
            # presented as if it covered every original book in the merge.
            root, _ = parse_opf(zf)
            originals = sum(e.get('media-type') == 'origrootfile/xml'
                            for e in find_all(root, 'item')) if root is not None else 0
            if not originals or originals == len(records):
                for key, total in (('numWords', 'numWords'),
                                   ('numChapters', 'collectionChapterCount')):
                    values = [parse_count(r.get(key)) for r in records]
                    if all(v is not None for v in values):
                        fields[total] = sum(values)
            sources.update({k: 'collection_stories' for k in fields if k not in sources})
    else:
        reported = _series_page_fields(zf)
        fields.update(reported)
        sources.update({k: 'collection_series_page' for k in reported})
    return fields, sources


def _series_page_fields(zf):
    root, path = parse_opf(zf)
    if root is None:
        return {}
    for item in spine_item_paths(zf, root, path):
        page = parse_xhtml(zf, item)
        if page is None:
            continue
        for dl in find_all(page, 'dl'):
            pairs = {}
            label = None
            for child in dl:
                if local_name(child.tag) == 'dt':
                    label = text_content(child).strip().rstrip(':').lower()
                elif local_name(child.tag) == 'dd' and label:
                    pairs[label] = text_content(child).strip()
                    label = None
            if 'works' not in pairs or 'complete' not in pairs:
                continue
            result = {}
            for label, key in (('works', 'collectionStoryCount'), ('words', 'numWords')):
                n = parse_count(pairs.get(label))
                if n is not None:
                    result[key] = n
            if pairs['complete'].lower() in ('yes', 'no'):
                result['collectionStatus'] = ('Completed' if pairs['complete'].lower() == 'yes'
                                              else 'In-Progress')
            # These are series dates, not the dates of the first work.
            for outer in find_all(page, 'dl'):
                current = None
                for child in outer:
                    if local_name(child.tag) == 'dt':
                        current = text_content(child).strip().rstrip(':').lower()
                    elif local_name(child.tag) == 'dd':
                        key = {'series begun': 'collectionDateBegun',
                               'series updated': 'collectionDateUpdated'}.get(current)
                        date = _parse_date(text_content(child).strip()) if key else None
                        if date is not None:
                            result[key] = date
                        current = None
            return result
    return {}
