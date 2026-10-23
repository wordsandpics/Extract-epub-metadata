"""Recognizable spaced archive and OTW PDF-style TXT prefaces.

Each reader requires its own opening signature and an explicit end to metadata.
Unlabeled values in detached/OCR columns are never matched by position.
"""
import re
from urllib.parse import urlsplit


_LABEL = re.compile(r'^([A-Za-z][A-Za-z /_-]{0,39}):\s*(.*)$')
_INLINE_BYLINE = re.compile(r'^(.+)\s+by\s+(.+)$', re.I)
_BYLINE = re.compile(r'^by\s+(.+)$', re.I)
_NOTICE = re.compile(r'^Posted originally on (?:the )?.+? at\s+(https?://[^\s]+/works/\d+)\.?$', re.I)
_STATS_START = re.compile(r'^(?:Stats:\s*)?(?:Published|Updated|Completed|Words|Chapters):', re.I)
_STAT = re.compile(r'(?:^|\s)(Published|Updated|Completed|Words|Chapters):\s*(.*?)'
                   r'(?=\s+(?:Published|Updated|Completed|Words|Chapters):|$)', re.I)
_OTW_LABELS = {
    'rating': 'rating', 'archive warning': 'warnings', 'archive warnings': 'warnings',
    'category': 'ao3categories', 'categories': 'ao3categories',
    'fandom': 'fandoms', 'fandoms': 'fandoms', 'relationship': 'ships',
    'relationships': 'ships', 'character': 'characters', 'characters': 'characters',
    'additional tags': 'freeformtags', 'language': 'language',
}
_TAG_KEYS = {'genre', 'category', 'ao3categories', 'fandoms', 'ships',
             'characters', 'warnings', 'freeformtags'}


def _label(line):
    match = _LABEL.fullmatch(line.strip())
    if match:
        return ' '.join(match[1].lower().replace('_', ' ').split()), match[2].strip()
    return None, None


def _join(lines):
    # Remove only layout whitespace. Do not repair OCR spelling or punctuation.
    return ' '.join(line.strip() for line in lines if line.strip())


def _paragraphs(lines):
    paragraphs, current = [], []
    for line in lines + ['']:
        if line.strip():
            current.append(line)
        elif current:
            paragraphs.append(_join(current))
            current = []
    return '\n\n'.join(paragraphs)


def _blocks(lines, keys):
    """Labeled wrapped values; unknown labels terminate the preceding value."""
    blocks, current, current_key, previous_blank = [], None, None, True
    for line in lines:
        label, value = _label(line)
        if label is not None:
            # A wrapped tag may itself contain a colon ("Dead Dove: Do Not
            # Eat"). Keep it when it continues the previous printed tag line.
            if label not in keys and current is not None and current_key in _TAG_KEYS and not previous_blank:
                current.append(line)
                previous_blank = False
                continue
            current = [] if label in keys else None
            current_key = keys.get(label)
            if current is not None:
                current.append(value)
                blocks.append((keys[label], current))
        elif line.strip() and current is not None:
            current.append(line)
        previous_blank = not line.strip()
    result = {}
    for key, lines in blocks:
        value = _join(lines)
        if value:
            if key in result and result[key] != value:
                result[key] = None
            else:
                result.setdefault(key, value)
    return {key: value for key, value in result.items() if value is not None}


def parse_spaced_archive(lines, labels):
    match = _INLINE_BYLINE.fullmatch(lines[0].strip()) if lines else None
    if not match:
        return {}
    title, author = match[1].strip(), match[2].strip()
    summary = next((i for i, line in enumerate(lines[1:], 1)
                    if _label(line)[0] in ('summary', 'description')), None)
    if summary is None:
        return {}
    # The repeated title is the archive's explicit boundary before chapter text.
    end = next((i for i in range(summary + 1, len(lines))
                if lines[i].strip() == title and not lines[i - 1].strip()
                and i + 1 < len(lines) and not lines[i + 1].strip()), None)
    if end is None:
        return {}
    keys = {label: key for label, key in labels.items()
            if key not in ('title', 'author', 'description')}
    fields = _blocks(lines[1:summary], keys)
    if len(fields) < 4 or not fields.get('site') or not fields.get('numWords'):
        return {}
    fields.update(title=title, author=[author], _txt_source='txt_spaced_header')
    inline_summary = _label(lines[summary])[1]
    description = _paragraphs(([inline_summary] if inline_summary else []) + lines[summary + 1:end])
    if description:
        fields['description'] = description
    if fields.get('ships'):
        fields['ships'] = re.sub(r'\s*/\s*', '/', fields['ships'])
    return fields


def _stats(lines):
    # Use explicit stat labels even when other columns have been detached.
    segments, current = [], None
    for line in lines:
        text = line.strip()
        if _STATS_START.match(text):
            current = [re.sub(r'^Stats:\s*', '', text, flags=re.I)]
            segments.append(current)
        elif text and current is not None and re.fullmatch(r'[\d,/?\s-]+', text):
            current.append(text)
        elif text:
            current = None
    result = {}
    chapter_values = set()
    for segment in segments:
        for match in _STAT.finditer(_join(segment)):
            label, value = match[1].lower(), match[2].strip()
            if label == 'chapters':
                chapter_values.add(value)
                if len(chapter_values) > 1:
                    for key in ('numChapters', 'numChaptersTotal', 'chapterslashtotal', 'status'):
                        result.pop(key, None)
                    continue
                chapters = re.fullmatch(r'(\d+)\s*/\s*(\d+|\?)', value)
                if chapters:
                    n, total = chapters.groups()
                    result.update(numChapters=n, chapterslashtotal=n + '/' + total)
                    if total != '?':
                        result['numChaptersTotal'] = total
                        if int(n) <= int(total):
                            result['status'] = 'Completed' if int(n) == int(total) else 'In-Progress'
            else:
                key = {'published': 'datePublished', 'updated': 'dateUpdated',
                       'completed': 'dateUpdated', 'words': 'numWords'}[label]
                if key in result and result[key] != value:
                    result[key] = None
                else:
                    result.setdefault(key, value)
    return {key: value for key, value in result.items() if value is not None}


def parse_pdf_preface(lines):
    if len(lines) < 3:
        return {}
    title = lines[0].strip()
    notice_start = next((i for i in range(1, min(5, len(lines))) if lines[i].strip()), None)
    if notice_start is None or not lines[notice_start].strip().lower().startswith('posted originally on '):
        return {}
    notice, notice_end = None, None
    for end in range(notice_start + 1, min(notice_start + 4, len(lines)) + 1):
        notice = _NOTICE.fullmatch(_join(lines[notice_start:end]))
        if notice:
            notice_end = end
            break
    if notice_end is None:
        return {}
    url = notice[1]
    try:
        host = (urlsplit(url).hostname or '').lower()
    except ValueError:
        return {}
    if host not in ('archiveofourown.org', 'www.archiveofourown.org',
                    'download.archiveofourown.org', 'squidgeworld.org', 'www.squidgeworld.org'):
        return {}
    # Require the repeated title and explicit byline after the metadata block.
    title_end, byline_end, author = None, None, None
    for i in range(notice_end, len(lines)):
        if lines[i].strip() != title:
            continue
        j = next((j for j in range(i + 1, len(lines)) if lines[j].strip()), None)
        byline = _BYLINE.fullmatch(lines[j].strip()) if j is not None else None
        if byline:
            title_end, byline_end, author = i, j, byline[1].strip()
            break
    if title_end is None:
        return {}
    header = lines[notice_end:title_end]
    tag_labels = [_label(line) for line in header if _label(line)[0] in _OTW_LABELS]
    if len(tag_labels) < 2:
        return {}
    detached = sum(not value for label, value in tag_labels) >= 2
    # Detached columns can shift every tag assignment. Keep explicit facts only.
    fields = {} if detached else _blocks(header, _OTW_LABELS | {'series': 'series', 'stats': '_stats'})
    fields.pop('_stats', None)
    if fields.get('series'):
        series = re.fullmatch(r'Part (\d+(?:\.\d+)?) of (.+)', fields['series'])
        if series:
            fields['series'] = '%s [%s]' % (series[2], series[1])
        else:
            del fields['series']
    fields.update(_stats(header))
    fields.update(title=title, storyUrl=url,
                  _txt_source='txt_pdf_partial' if detached else 'txt_pdf_preface')
    if not detached:
        fields['author'] = [author]
    summary = next((i for i in range(byline_end + 1, len(lines)) if lines[i].strip()), None)
    if summary is not None and lines[summary].strip().rstrip(':').lower() == 'summary':
        # Without a clear section boundary, leave the summary out rather than
        # consume chapter text. Markers are whole lines, not words inside prose.
        end = next((i for i in range(summary + 1, len(lines))
                    if lines[i].strip().rstrip(':').lower() in ('notes', 'chapter notes', 'work text')
                    or re.fullmatch(r'Chapter\s+\d+(?:[.:].*)?', lines[i].strip(), re.I)), None)
        if end is not None:
            description = _paragraphs(lines[summary + 1:end])
            if description:
                fields['description'] = description
    return fields
