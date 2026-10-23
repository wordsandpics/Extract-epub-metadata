"""
Tier "3c": AO3's own *PDF* download, converted to EPUB (e.g. by Calibre) --
confirmed against tests/fixtures/ao3-pdf-wrapped-preface.epub. The PDF keeps AO3's
standard preface page, but conversion flattens it to one block element per
printed line, with no structure left at all:

    <h2>Posted originally on the<a> Archive of Our Own</a> at</h2>
    <p><a href="http://download.archiveofourown.org/works/98000260">http://...</a>.</p>
    <p>Rating:               <a>Mature</a></p>
    <p>Character:            <a>Test Character A</a>, ... <a>Test Character B</a></p>
    <p><a>Synthetic Surname</a></p>                        <- wrapped continuation
    <p>Series:                Part 2 of<a href=".../series/98000261"> Synthetic PDF Series</a></p>
    <p>Stats: <span>Published: 2016-12-21 Updated: 2017-10-10 Chapters: 3/? Words:</span></p>
    <p>15504</p>
    <p> </p>
    <p><b>Synthetic PDF Series: Overtime</b></p>
    <p>by<a href=".../users/TestWriterPDF/pseuds/TestWriterPDF"> TestWriterPDF</a></p>
    <p>Summary</p>
    <p>...one <p> per printed line...</p>

So everything here is read from the *text*, line by line: a "Label:" line
starts a field, following lines continue it until a blank line or the next
label. Tag links are deliberately NOT used for tag values -- the PDF's link
areas come through misaligned (commas linked to the wrong tag, one link
spanning "Fluff, Christmas Presents, England (Country), overseas visits",
three of those tags with no link of their own). The text is reliable, and
AO3 forbids commas inside tag names, so splitting the joined text on commas
is safe.
"""
import re
from urllib.parse import quote

from ._epubxml import find_all, local_name, parse_opf, parse_xhtml, spine_item_paths, text_content
from .ao3_frontmatter import _DT_TO_KEY, _SCALAR_KEYS, _parse_stats, parse_series, series_fields

_BLOCK_TAGS = {'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'}
_HEADER_PREFIX = 'posted originally on the archive of our own'
_WORK_URL_RE = re.compile(r'https?://(?:www\.|download\.)?archiveofourown\.org/works/\d+', re.I)
_LABEL_RE = re.compile(r'^([A-Za-z][A-Za-z ]{1,25}):\s*(.*)$')
# Labels AO3's preface can carry -- 'collections' is recognized only so it
# ends the previous field instead of being read as its continuation.
_KNOWN_LABELS = set(_DT_TO_KEY) | {'stats', 'series', 'collections', 'collection'}
# A "Stats:" value only continues onto lines that still look like stats
# (the wrapped "15504" above), so a missing blank line can't make the
# title get swallowed as part of it.
_STATS_CONTINUATION_RE = re.compile(
    r'^[\d,/?\s]+$|\b(?:Published|Updated|Completed|Words|Chapters|Comments|Kudos|Bookmarks|Hits):')
_SUMMARY_STOP = {'notes', 'chapter notes', 'chapter summary', 'chapter end notes'}
_PSEUD_USER_RE = re.compile(r'^(.+?)\s+\((.+)\)$')
_SENTENCE_END_RE = re.compile(r'[.!?:"”\')]$')


def _lines(root):
    """[(normalized text, element)] for every block element, in order."""
    return [(' '.join(text_content(e).split()), e)
            for e in root.iter() if local_name(e.tag) in _BLOCK_TAGS]


def _join_wrapped(texts):
    """Rejoin a value the PDF wrapped over several lines: a space between
    lines, except after a mid-word hyphen ("Self-" + "Harm")."""
    out = ''
    for text in texts:
        if not out:
            out = text
        elif re.search(r'\S-$', out):
            out += text
        else:
            out += ' ' + text
    return out


def _authors(byline_text):
    """FanFicFare's AO3 author fields (base_otw_adapter.py) from the byline
    text alone: author = the displayed name ("pseud (username)" when they
    differ), authorId = the pseud, authorUrl = the pseud's AO3 URL. Text,
    not links, for the same misaligned-link reason as the tags."""
    names = [n.strip() for n in byline_text.split(',') if n.strip()]
    result = {'author': names}
    if names and all(n != 'Anonymous' for n in names):
        ids, urls = [], []
        for name in names:
            m = _PSEUD_USER_RE.match(name)
            pseud, user = (m.group(1), m.group(2)) if m else (name, name)
            ids.append(pseud)
            urls.append('https://archiveofourown.org/users/%s/pseuds/%s' % (
                quote(user), quote(pseud)))
        result['authorId'] = ids
        result['authorUrl'] = urls
    return result


def _parse_preface(lines, start):
    result = {}

    header_text = ' '.join(t for t, _e in lines[start:start + 3])
    hrefs = [e.get('href') or '' for _t, el in lines[start:start + 3] for e in find_all(el, 'a')]
    m = _WORK_URL_RE.search(header_text) or next(
        (m for m in (_WORK_URL_RE.search(h) for h in hrefs) if m), None)
    if m:
        result['storyUrl'] = m.group(0)

    fields = []          # [(label, [text], [element])]
    current = None
    i = start + 1
    while i < len(lines):
        text, elem = lines[i]
        m = _LABEL_RE.match(text)
        if m and m.group(1).strip().lower() in _KNOWN_LABELS:
            current = (m.group(1).strip().lower(), [m.group(2)], [elem])
            fields.append(current)
        elif not text:
            if fields:
                current = None
        elif current is not None and (current[0] != 'stats' or _STATS_CONTINUATION_RE.search(text)):
            current[1].append(text)
            current[2].append(elem)
        elif fields:
            break           # first line past the label block: the title
        i += 1

    for label, texts, elems in fields:
        value = _join_wrapped([t for t in texts if t])
        if label == 'stats':
            _parse_stats(value, result)
        elif label == 'series':
            result.update(series_fields(parse_series(elems)))
        elif label in _DT_TO_KEY and value:
            key = _DT_TO_KEY[label]
            if key in _SCALAR_KEYS:
                result[key] = value
            else:
                result[key] = [v.strip() for v in value.split(',') if v.strip()]

    # Title, then "by ...", then "Summary" and its lines.
    if i < len(lines) and lines[i][0]:
        result['title'] = lines[i][0]
        i += 1
    while i < len(lines) and not lines[i][0]:
        i += 1
    if i < len(lines) and lines[i][0].startswith('by '):
        result.update(_authors(lines[i][0][3:]))
        result['byline'] = lines[i][0][3:].strip()
        i += 1
    while i < len(lines) and not lines[i][0]:
        i += 1
    if i < len(lines) and lines[i][0].rstrip(':').lower() == 'summary':
        paragraphs, current_para = [], []
        for text, _elem in lines[i + 1:]:
            if text.rstrip(':').lower() in _SUMMARY_STOP:
                break
            if not text:
                if current_para:
                    paragraphs.append(current_para)
                    current_para = []
                continue
            current_para.append(text)
            # One <p> per printed line, so real paragraph breaks are lost:
            # a line ending a sentence is taken to end its paragraph too.
            if _SENTENCE_END_RE.search(text):
                paragraphs.append(current_para)
                current_para = []
        if current_para:
            paragraphs.append(current_para)
        summary = '\n\n'.join(_join_wrapped(p) for p in paragraphs if p)
        if summary:
            result['description'] = summary

    return result


def extract_ao3_pdf_preface(zf):
    opf_root, opf_path = parse_opf(zf)
    if opf_root is None:
        return None

    for path in spine_item_paths(zf, opf_root, opf_path):
        root = parse_xhtml(zf, path)
        if root is None:
            continue
        lines = _lines(root)
        for index, (text, _elem) in enumerate(lines):
            if text.lower().startswith(_HEADER_PREFIX):
                result = _parse_preface(lines, index)
                return result or None
    return None
