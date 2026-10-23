"""Opening archive headers in TXT files; never scan chapters for metadata.

Recognizes compact title/byline headers plus explicit spaced-archive and
PDF-style prefaces. Each layout has its own boundaries; ordinary chapters and
notice-heavy saved web pages cannot establish that a header is genuine.
"""
import codecs
import re
from urllib.parse import urlsplit

from .txt_prefaces import parse_spaced_archive, parse_pdf_preface


MAX_HEADER_BYTES = 65536
MAX_HEADER_LINES = 200
_LABEL_RE = re.compile(r'^([A-Za-z][A-Za-z /_-]{0,39})\s*:\s*(.*)$')
_BYLINE_RE = re.compile(r'^by\s+(.+)$', re.IGNORECASE)

# Explicit aliases only. Lists, dates and counts are normalized by mapping.py.
LABEL_TO_KEY = {
    'title': 'title', 'author': 'author', 'authors': 'author',
    'category': 'category', 'fandom': 'fandoms', 'fandoms': 'fandoms',
    'genre': 'genre', 'language': 'language', 'characters': 'characters',
    'ships': 'ships', 'relationships': 'ships', 'warnings': 'warnings',
    'status': 'status', 'published': 'datePublished', 'updated': 'dateUpdated',
    'packaged': 'dateCreated', 'rating': 'rating', 'rated': 'rating',
    'chapters': 'numChapters', 'chapter count': 'numChapters',
    'words': 'numWords', 'word count': 'numWords', 'publisher': 'site',
    'story url': 'storyUrl', 'author url': 'authorUrl',
    'summary': 'description', 'description': 'description',
}


def _label_key(label):
    return LABEL_TO_KEY.get(' '.join(label.lower().replace('_', ' ').split()))


def extract_txt_header(stream):
    """Read a bounded prefix from an open binary/text stream; return raw fields.

    UTF-8, BOM-marked UTF-16 and legacy Windows-1252 are supported. Decoding
    never inserts replacement characters. Bounded incremental decoding avoids
    misidentifying a UTF-8 file when the prefix ends inside a character.
    """
    prefix = stream.read(MAX_HEADER_BYTES)
    if isinstance(prefix, bytes):
        if prefix.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)):
            encoding = 'utf-16'
        else:
            encoding = 'utf-8-sig'
        try:
            prefix = codecs.getincrementaldecoder(encoding)().decode(prefix, final=False)
        except UnicodeDecodeError:
            if encoding == 'utf-16':
                return {}
            prefix = prefix.decode('cp1252')
    return parse_txt_header(prefix)


def parse_txt_header(text):
    lines = text.lstrip('\ufeff').splitlines()[:MAX_HEADER_LINES]
    # Permit leading whitespace, but do not hunt for metadata later in a file.
    start = next((i for i, line in enumerate(lines) if line.strip()), len(lines))
    if start == len(lines):
        return {}
    preface = parse_pdf_preface(lines[start:]) or parse_spaced_archive(lines[start:], LABEL_TO_KEY)
    if preface:
        return _clean_fields(preface)
    fields = {}
    first = lines[start].strip()
    # Check the byline first: an ordinary story title can itself contain a colon.
    following = next((i for i in range(start + 1, len(lines)) if lines[i].strip()), None)
    byline = _BYLINE_RE.fullmatch(lines[following].strip()) if following is not None else None
    if byline:
        fields = {'title': first, 'author': [byline.group(1).strip()]}
        start = following + 1
        while start < len(lines) and not lines[start].strip():
            start += 1
    elif not _LABEL_RE.match(first):
        return {}

    recognized = set()
    ended = False
    for line in lines[start:]:
        stripped = line.strip()
        if not stripped:
            ended = True
            break
        match = _LABEL_RE.fullmatch(stripped)
        if match is None:
            ended = True
            break
        key = _label_key(match.group(1))
        value = match.group(2).strip()
        if key and value:
            recognized.add(key)
            # Conflicting aliases/duplicate values are ambiguous; omit the field.
            value = [value] if key == 'author' else value
            if key in fields and fields[key] != value:
                fields[key] = None
            else:
                fields.setdefault(key, value)

    # Require an identity plus multiple factual labels, not a title/byline alone
    # or a prose paragraph that happens to begin with "Summary:".
    facts = recognized - {'title', 'author', 'description'}
    if not ended or not fields.get('title') or not fields.get('author') or len(facts) < 2:
        return {}
    fields = {key: value for key, value in fields.items() if value is not None}
    return _clean_fields(fields)


def _clean_fields(fields):
    for key in ('storyUrl', 'authorUrl'):
        if key in fields:
            try:
                url = urlsplit(fields[key])
                valid = url.scheme in ('http', 'https') and url.hostname and not re.search(r'\s', fields[key])
            except ValueError:
                valid = False
            if not valid:
                del fields[key]
    if fields.get('site'):
        # Publisher labels in these exports use "www.fanfiction.net".
        fields['site'] = re.sub(r'^www\.', '', fields['site'], flags=re.IGNORECASE)
    return fields
