"""Bounded AO3 PDF download headers, using Calibre's bundled Poppler tool.

Only the download notice plus a labeled header and an explicit byline qualify.
Browser printouts and image-only pages are not treated as archive headers.
"""
import re
from copy import deepcopy
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

from .ao3_frontmatter import _DT_TO_KEY, _SCALAR_KEYS, _parse_stats, parse_series, series_fields
from ._urls import canonical_ao3_url

MAX_PAGES = 5
MAX_XML_BYTES = 2 * 1024 * 1024
_LABEL = re.compile(r'^([A-Za-z][A-Za-z ]{1,25}):\s*(.*)$')
_LABELS = set(_DT_TO_KEY) | {'stats', 'series', 'collections', 'collection'}
_NOTICE = re.compile(r'^Posted originally on the Archive of Our Own at\s+(https?://(?:www\.|download\.)?archiveofourown\.org/works/\d+)\s*\.?$', re.I)
_PROFILE = re.compile(r'(?:https?://(?:www\.|download\.)?archiveofourown\.org)?(/users/([^/?#]+)/pseuds/([^/?#]+))$')


def _text(elem):
    return ' '.join(''.join(elem.itertext()).split())


def _rows(root):
    rows = []
    for page in root.findall('page')[:MAX_PAGES]:
        groups = []
        for elem in sorted(page.findall('text'), key=lambda e: (float(e.get('top', 0)), float(e.get('left', 0)))):
            if not _text(elem):
                continue
            top, height = float(elem.get('top', 0)), float(elem.get('height', 12))
            center = top + height / 2
            if groups and abs(center - groups[-1][0]) <= min(height, groups[-1][1]) * .45:
                groups[-1][2].append(elem)
            else:
                groups.append((center, height, [elem]))
        for _center, _height, elems in groups:
            p = ET.Element('p')
            previous_end = None
            for elem in sorted(elems, key=lambda e: float(e.get('left', 0))):
                left = float(elem.get('left', 0))
                if previous_end is not None and left - previous_end > 2:
                    spacer = ET.SubElement(p, 'span'); spacer.text = ' '
                # Keep text and explicit links, including wrapped series names.
                span = ET.SubElement(p, 'span'); span.text = elem.text
                for child in elem:
                    span.append(deepcopy(child))
                previous_end = left + float(elem.get('width', 0))
            rows.append((_text(p), p, int(page.get('number', 1))))
    return rows


def parse_pdf_xml(data):
    """Pure parser for bounded pdftohtml XML; returns (fields, partial)."""
    if len(data) > MAX_XML_BYTES:
        raise ValueError('The PDF opening pages contain too much metadata to inspect safely.')
    root = ET.fromstring(data)
    rows = _rows(root)
    notice_end, story_url, notice_start = None, None, None
    for start in range(min(6, len(rows))):
        if not rows[start][0].lower().startswith('posted originally on '):
            continue
        for end in range(start + 1, min(start + 5, len(rows)) + 1):
            notice = _NOTICE.fullmatch(' '.join(row[0] for row in rows[start:end]))
            if notice:
                notice_start, notice_end, story_url = start, end, canonical_ao3_url(notice[1])
                break
        if notice_end is not None:
            break
    if notice_end is None:
        return {}, False
    title_before = ' '.join(row[0] for row in rows[:notice_start])
    byline_index = next((i for i in range(notice_end, len(rows)) if re.match(r'^by\s+\S', rows[i][0])), None)
    if byline_index is None or byline_index <= notice_end:
        return {}, False
    title_index = byline_index - 1
    title = rows[title_index][0]
    if title_before and title != title_before:
        # A wrapped repeated title can occupy more than one printed line.
        match = next((i for i in range(max(notice_end, byline_index - 3), byline_index)
                      if ' '.join(r[0] for r in rows[i:byline_index]) == title_before), None)
        if match is None:
            return {}, False
        title_index, title = match, title_before
    header = rows[notice_end:title_index]
    blocks, current = [], None
    for value, elem, _page in header:
        label = _LABEL.fullmatch(value)
        if label and label[1].lower() in _LABELS:
            current = (label[1].lower(), [label[2]], [elem]); blocks.append(current)
        elif current:
            current[1].append(value); current[2].append(elem)
    if len({label for label, _, _ in blocks} & set(_DT_TO_KEY)) < 2 or not any(b[0] == 'stats' for b in blocks):
        return {}, False
    fields = {'title': title, 'storyUrl': story_url}
    partial, seen = False, set()
    stat_values = {}
    for label, texts, elems in blocks:
        value = ' '.join(t for t in texts if t)
        key = _DT_TO_KEY.get(label)
        if label == 'stats':
            parsed = {}; _parse_stats(value, parsed)
            for key, item in parsed.items():
                stat_values.setdefault(key, set()).add(item)
        elif label == 'series':
            # PDF link rectangles can include 'Part N of' or a following
            # comma. Read the explicit series text; never guess by comma.
            plain = ET.Element('p'); plain.text = value
            entries = parse_series([plain])
            urls = list(dict.fromkeys(canonical_ao3_url(a.get('href', ''))
                        for e in elems for a in e.iter('a')
                        if '/series/' in a.get('href', '')))
            urls = [u for u in urls if u]
            if len(urls) == len(entries):
                entries = [(name, index, url) for (name, index, _), url in zip(entries, urls)]
            fields.update(series_fields(entries))
        elif key and value:
            if key in seen:
                fields.pop(key, None); partial = True
                continue
            seen.add(key)
            if key in _SCALAR_KEYS:
                if key == 'language' and not all(c.isalpha() or c in ' -()' for c in value):
                    partial = True
                else:
                    fields[key] = value
            else:
                # AO3 tag values are comma-delimited; PDF annotation areas can
                # be shifted, so visible text determines the values.
                fields[key] = [v.strip() for v in value.split(',') if v.strip()]
    for key, values in stat_values.items():
        if len(values) == 1:
            fields[key] = next(iter(values))
        else:
            partial = True
    chapter_keys = ('numChapters', 'numChaptersTotal', 'chapterslashtotal', 'status')
    if any(len(stat_values.get(key, ())) > 1 for key in chapter_keys):
        for key in chapter_keys:
            fields.pop(key, None)
    if fields.get('numChaptersTotal') and int(fields.get('numChapters', 0)) > int(fields['numChaptersTotal']):
        for key in chapter_keys:
            fields.pop(key, None)
        partial = True
    byline, elem, _ = rows[byline_index]
    fields['author'] = [s.strip() for s in byline[3:].split(',') if s.strip()]
    linked_names = {}
    for a in elem.iter('a'):
        match = _PROFILE.fullmatch(a.get('href', ''))
        if match and _text(a):
            linked_names.setdefault((match[1], match[3]), []).append(_text(a))
    profiles = [(re.sub(r'^by\s+', '', ' '.join(parts)).strip(' ,'), path, pseud)
                for (path, pseud), parts in linked_names.items()]
    # Names come from the byline. Profile URLs must agree with those names;
    # other credits/translations elsewhere in the PDF cannot become authors.
    if [p[0] for p in profiles] == fields['author']:
        fields['authorUrl'] = ['https://archiveofourown.org' + p[1] for p in profiles]
        fields['authorId'] = [p[2] for p in profiles]
    summary = byline_index + 1
    if summary < len(rows) and rows[summary][0].rstrip(':').lower() == 'summary':
        end = next((i for i in range(summary + 1, len(rows))
                    if rows[i][0].rstrip(':').lower() in ('notes', 'chapter notes', 'work text')
                    or re.match(r'^(?:Chapter\s+\d+\b|Prologue\b|Epilogue\b)', rows[i][0], re.I)
                    or (rows[i][2] > rows[i - 1][2] and len(rows[i][0]) < 150
                        and any(True for _ in rows[i][1].iter('b')))), None)
        if end is not None:
            fields['description'] = ' '.join(r[0] for r in rows[summary + 1:end]).strip()
        else:
            partial = True
    return fields, partial


def extract_pdf_header(stream):
    # Lazy import keeps the parser testable without Calibre, which supplies
    # the platform-specific binary path. Older Calibre has no shared flags value.
    from calibre.ebooks.pdf.pdftohtml import PDFTOHTML
    creationflags = subprocess.DETACHED_PROCESS if sys.platform == 'win32' else 0
    with tempfile.TemporaryDirectory(prefix='extract-ao3-pdf-') as folder:
        path = Path(folder) / 'input.pdf'
        with path.open('wb') as dest:
            shutil.copyfileobj(stream, dest)
        try:
            result = subprocess.run([PDFTOHTML, '-xml', '-i', '-f', '1', '-l', str(MAX_PAGES),
                                     '-enc', 'UTF-8', '-stdout', str(path)],
                                    stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    timeout=30, creationflags=creationflags)
        except subprocess.TimeoutExpired:
            raise ValueError('Reading the PDF opening pages exceeded the 30-second limit.') from None
        if result.returncode:
            raise ValueError('The PDF opening pages could not be read. It may be encrypted or damaged.')
        return parse_pdf_xml(result.stdout)
