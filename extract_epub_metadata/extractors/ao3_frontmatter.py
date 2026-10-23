"""
Tier 3: AO3's own native "preface" front matter, verified directly against
a real AO3-downloaded EPUB (see tests/fixtures/ao3-native-complete.epub):

    <div id="preface">
      <p class="message">
        <b>{title}</b><br/>
        Posted originally on the <a href="https://archiveofourown.org/">Archive of Our Own</a>
        at <a href="https://archiveofourown.org/works/{storyId}">https://.../works/{storyId}</a>.
      </p>
      <dl class="tags">
        <dt>Rating:</dt><dd><a ...>General Audiences</a></dd>
        <dt>Archive Warning:</dt><dd><a ...>...</a></dd>
        <dt>Category:</dt><dd><a ...>M/M</a></dd>
        <dt>Fandom:</dt><dd><a ...>...</a></dd>
        <dt>Relationships:</dt><dd><a ...>...</a>, <a ...>...</a></dd>
        <dt>Characters:</dt><dd><a ...>...</a>, ...</dd>
        <dt>Additional Tags:</dt><dd><a ...>...</a>, ...</dd>
        <dt>Language:</dt><dd>English</dd>
        <dt>Stats:</dt><dd>Published: 2026-07-14\\nWords: 1,013\\nChapters: 1/1</dd>
      </dl>
    </div>

Field-name mapping to FanFicFare's raw (per-key, pre-composite) vocabulary
is taken directly from fanficfare/adapters/base_otw_adapter.py -- category
and genre are NOT emitted here; FFF composites those at read time from
fandoms/freeformtags/ao3categories via personal.ini's include_in_category/
include_in_genre, so emitting the raw keys keeps that composition working
unmodified.

Also handles a second, related shape: AO3's live *work page* metadata
block, copied verbatim into an "Information" page by WebToEpub (confirmed
against tests/fixtures/ao3-wayback-information.epub, a WebToEpub download of an
AO3 work via its Wayback Machine snapshot):

    <dl class="work meta group">
      <dt class="rating tags">Rating:</dt><dd class="rating tags"><ul><li><a>Explicit</a></li></ul></dd>
      ...same labels as the preface's dl.tags...
      <dt class="stats">Stats:</dt>
      <dd class="stats"><dl class="stats"><dt>Published:</dt><dd>2016-03-06</dd>...</dl></dd>
    </dl>
    <div class="summary module"><blockquote class="userstuff"><p>...</p></blockquote></div>

It has no preface message paragraph (so no title/story link -- those come
from the OPF), and its tag links are useless chrome-extension:// hrefs
WebToEpub rewrote, but the dt/dd pairs are label-for-label identical, so
both shapes share one dt/dd loop below.

A third variant is the same work page saved whole by a generic "save page
as EPUB" browser extension (confirmed against tests/fixtures/
ao3-wayback-whole-page.epub, also a Wayback snapshot) -- which strips every
`class` attribute, so none of the above is detectable by class. Everything
past the preface is therefore found by AO3's own visible text labels
("Rating:", "Summary:") and the element ids that do survive (`workskin`),
never by class alone. That variant also carries the work's title (<h2>)
and byline (<h3> of /users/<id>/pseuds/<pseud> links) inside
<div id="workskin">, which are recovered too.
"""
import re


from ._urls import canonical_ao3_url, unwrap_wayback_url
from ._epubxml import (
    find_all, find_first, local_name, parse_opf, parse_xhtml, spine_item_paths, text_content,
)


# AO3 singularizes/pluralizes several of these dt labels depending on how
# many tags are in that category (e.g. "Relationship:" for exactly one
# pairing, "Relationships:" for more than one) -- confirmed against
# tests/fixtures/ao3-anonymous-singular-tags.epub, a single-pairing work whose
# "Relationship:" label was previously unrecognized (only the plural form
# was registered), silently dropping ships entirely. Both forms are
# registered for every category known to vary this way.
_DT_TO_KEY = {
    'rating': 'rating',
    'archive warning': 'warnings',
    'archive warnings': 'warnings',
    'category': 'ao3categories',
    'fandom': 'fandoms',
    'fandoms': 'fandoms',
    'relationship': 'ships',
    'relationships': 'ships',
    'character': 'characters',
    'characters': 'characters',
    'additional tags': 'freeformtags',
    'language': 'language',
}
_SCALAR_KEYS = {'rating', 'language'}

_WORKS_URL_RE = re.compile(r'/works/(\d+)')
_WORDS_RE = re.compile(r'Words:\s*([0-9][0-9, \u00a0\u2007\u2009\u202f]*)')
# Digits/'?' only, not \S+ -- the work-page shape's nested stats <dl> has
# no whitespace between entries once flattened ("Chapters:1/1Comments:41"),
# and \S+ swallowed the rest of the line into the total, which then never
# equalled the numerator (real bug: a finished 1/1 work came out
# In-Progress with no total -- tests/fixtures/ao3-wayback-information.epub).
_CHAPTERS_RE = re.compile(r'Chapters:\s*(\d+|\?)\s*/\s*(\d+|\?)')
_PUBLISHED_RE = re.compile(r'Published:\s*([\d-]+)')
_UPDATED_RE = re.compile(r'Updated:\s*([\d-]+)')
_COMPLETED_RE = re.compile(r'Completed:\s*([\d-]+)')


def _find_preface(root):
    for div in find_all(root, 'div'):
        if div.get('id') == 'preface':
            return div
    return None


def _label(elem):
    """An AO3 dt/heading label, normalized: "Archive Warning:" -> "archive warning"."""
    text = ' '.join(text_content(elem).split()).lower()
    return text[:-1].strip() if text.endswith(':') else text


def _find_work_meta(root):
    """The work page's tags <dl>, recognized by its labels rather than its
    class (see module docstring): the first <dl> with a "Rating" dt plus
    at least one other AO3 tag-category dt. The nested stats <dl> never
    qualifies (no Rating), so this can't pick the inner one."""
    for dl in find_all(root, 'dl'):
        labels = {_label(dt) for dt in find_all(dl, 'dt')}
        if 'rating' in labels and len(labels & set(_DT_TO_KEY)) >= 2:
            return dl
    return None


def _text_with_breaks(elem):
    """Whitespace-normalized text, with <br/> kept as a line break --
    text_content() alone drops it, gluing the words either side together
    (a summary's "...in Synthetic line one<br/><a>Synthetic Information Page</a><br/>about"
    came out as "Synthetic line oneSynthetic Information Pageabout")."""
    def walk(e):
        parts = [e.text or '']
        for child in e:
            parts.append('\n' if local_name(child.tag) == 'br' else walk(child))
            parts.append(child.tail or '')
        return ''.join(parts)
    lines = (' '.join(line.split()) for line in walk(elem).split('\n'))
    return '\n'.join(line for line in lines if line)


def _find_work_summary(root):
    """The work summary as plain text, one paragraph per blank-line
    -separated block (Calibre's comments handling turns that back into
    <p>s), or None. Found as the <blockquote> following a "Summary:"
    heading in the same parent -- the first one on the page is the
    work's; later ones are per-chapter summaries."""
    for parent in root.iter():
        children = list(parent)
        for i, child in enumerate(children):
            if local_name(child.tag) not in ('h3', 'h4', 'p', 'b', 'strong') or _label(child) != 'summary':
                continue
            for sibling in children[i + 1:]:
                if local_name(sibling.tag) != 'blockquote':
                    continue
                paragraphs = [_text_with_breaks(p) for p in find_all(sibling, 'p')]
                paragraphs = [p for p in paragraphs if p]
                if not paragraphs:
                    text = ' '.join(text_content(sibling).split())
                    paragraphs = [text] if text else []
                if paragraphs:
                    return '\n\n'.join(paragraphs)
                break
    return None


_PSEUD_URL_RE = re.compile(r'/users/([^/?#]+)/pseuds/([^/?#]+)')


def _parse_download_authors(preface, result):
    """Native AO3 bylines mark individual pseud links with rel=author.

    Calibre may split the byline into the next spine document after the
    tags page, while the OPF combines all authors into one creator string.
    """
    links = []
    for a in find_all(preface, 'a'):
        if 'author' not in (a.get('rel') or '').split():
            continue
        href = unwrap_wayback_url(a.get('href') or '') or a.get('href') or ''
        match = _PSEUD_URL_RE.search(href)
        name = ' '.join(text_content(a).split())
        if match and name:
            links.append((name, match.group(1), match.group(2)))
    if links:
        result['author'] = [name for name, _user, _pseud in links]
        result['authorId'] = [pseud for _name, _user, pseud in links]
        result['authorUrl'] = ['https://archiveofourown.org/users/%s/pseuds/%s' % (user, pseud)
                               for _name, user, pseud in links]
        result['byline'] = ', '.join(result['author'])


def _parse_workskin_header(root, result):
    """Title and byline from <div id="workskin"> (whole-page saves only --
    WebToEpub's Information page has neither). Author fields mirror
    FanFicFare's own AO3 adapter (base_otw_adapter.py): author = the link
    text ("pseud (username)" when they differ), authorId = the pseud (the
    URL's last segment), authorUrl = the canonical pseud URL."""
    workskin = next((d for d in find_all(root, 'div') if d.get('id') == 'workskin'), None)
    if workskin is None:
        return
    h2 = find_first(workskin, 'h2')
    if h2 is not None:
        title = ' '.join(text_content(h2).split())
        if title:
            result['title'] = title
    for h3 in find_all(workskin, 'h3'):
        links = []
        for a in find_all(h3, 'a'):
            href = a.get('href') or ''
            m = _PSEUD_URL_RE.search(unwrap_wayback_url(href) or href)
            if m:
                links.append((' '.join(text_content(a).split()), m.group(1), m.group(2)))
        if not links:
            continue
        result['author'] = [name for name, _user, _pseud in links]
        result['authorId'] = [pseud for _name, _user, pseud in links]
        result['authorUrl'] = ['https://archiveofourown.org/users/%s/pseuds/%s' % (user, pseud)
                               for _name, user, pseud in links]
        result['byline'] = ' '.join(text_content(h3).split())
        return


_SERIES_POSITION_RE = re.compile(r'Part\s+(\d+)\s+of(?:\s+the)?\s*$', re.I)
_SERIES_TEXT_RE = re.compile(r'Part\s+(\d+)\s+of\s+(.+?)\s*(?=,\s*Part\s+\d+\s+of\s|$)', re.I)
_SERIES_HREF_RE = re.compile(r'/series/\d+')


def parse_series(elems):
    """[(name, index, url-or-None), ...] from AO3's "Part N of <a
    href=.../series/ID>Name</a>[, Part M of <a>Other</a>]" -- the same
    shape in AO3's own download preface, its work page, and its PDF
    preface (tests/fixtures/ao3-pdf-wrapped-preface.epub). Like FanFicFare's own AO3
    adapter, each /series/ link is paired with the "Part N of" text
    immediately before it; with no usable links (a PDF conversion can
    lose or misplace them), falls back to reading the plain text. `elems`
    is a list so a value wrapped over several lines can be passed whole."""
    found = []
    has_series_link = [False]
    pending = ['']

    def walk(e):
        pending[0] += e.text or ''
        for child in e:
            href = child.get('href') or ''
            if local_name(child.tag) == 'a' and _SERIES_HREF_RE.search(href):
                has_series_link[0] = True
                m = _SERIES_POSITION_RE.search(pending[0])
                name = ' '.join(text_content(child).split())
                if m and name:
                    url = canonical_ao3_url(unwrap_wayback_url(href) or href)
                    found.append((name, int(m.group(1)), url))
                pending[0] = ''
            else:
                walk(child)
            pending[0] += child.tail or ''

    for elem in elems:
        walk(elem)
    if found:
        return found
    if has_series_link[0]:
        return []  # do not reinterpret link/navigation text as a series title
    text = ' '.join(' '.join(text_content(e).split()) for e in elems)
    return [(m.group(2), int(m.group(1)), None) for m in _SERIES_TEXT_RE.finditer(text)]


def series_fields(entries):
    """FanFicFare's own series keys (base_otw_adapter.py): seriesNN /
    seriesNNUrl per series ("Name [N]", from 00), plus the first one as
    the main series/seriesUrl -- what Calibre's Series field gets."""
    result = {}
    for i, (name, index, url) in enumerate(entries):
        result['series%02d' % i] = '%s [%s]' % (name, index)
        if url:
            result['series%02dUrl' % i] = url
    if entries:
        result['series'] = result['series00']
        if 'series00Url' in result:
            result['seriesUrl'] = result['series00Url']
    return result


def _parse_dl(dl, result):
    dts = list(find_all(dl, 'dt'))
    dds = list(find_all(dl, 'dd'))
    for dt, dd in zip(dts, dds):
        label = _label(dt)

        if label == 'stats':
            _parse_stats(text_content(dd), result)
            continue
        if label == 'series':
            result.update(series_fields(parse_series([dd])))
            continue

        key = _DT_TO_KEY.get(label)
        if not key:
            continue

        tag_links = list(find_all(dd, 'a'))
        if tag_links:
            values = [text_content(a).strip() for a in tag_links if text_content(a).strip()]
        else:
            dd_text = text_content(dd).strip()
            values = [dd_text] if dd_text else []

        if not values:
            continue
        result[key] = values[0] if key in _SCALAR_KEYS else values


def _parse_stats(text, result):
    m = _WORDS_RE.search(text)
    if m:
        result['numWords'] = m.group(1).strip()
    m = _CHAPTERS_RE.search(text)
    if m:
        n, total = m.group(1), m.group(2)
        result['chapterslashtotal'] = '%s/%s' % (n, total)
        if n.isdigit():
            result['numChapters'] = n
        if total.isdigit():
            # A real planned-total ("12/24") is genuinely distinct data
            # from the current/downloaded count -- absent entirely for an
            # open-ended work ("12/?"), where there's nothing to recover.
            result['numChaptersTotal'] = total
        result['status'] = 'Completed' if n == total else 'In-Progress'
    m = _PUBLISHED_RE.search(text)
    if m:
        result['datePublished'] = m.group(1).strip()
        result.setdefault('dateUpdated', m.group(1).strip())
    m = _UPDATED_RE.search(text)
    if m:
        result['dateUpdated'] = m.group(1).strip()
    m = _COMPLETED_RE.search(text)
    if m:
        result['dateUpdated'] = m.group(1).strip()


def extract_ao3_frontmatter(zf):
    opf_root, opf_path = parse_opf(zf)
    if opf_root is None:
        return None

    download_result = {}
    for path in spine_item_paths(zf, opf_root, opf_path):
        root = parse_xhtml(zf, path)
        if root is None:
            continue
        preface = _find_preface(root)
        if preface is None:
            if download_result:
                return download_result
            work_meta = _find_work_meta(root)
            if work_meta is None:
                continue
            result = {}
            _parse_workskin_header(root, result)
            _parse_dl(work_meta, result)
            summary = _find_work_summary(root)
            if summary:
                result['description'] = summary
            if result:
                return result
            continue

        result = {}
        _parse_download_authors(preface, result)

        message = find_first(preface, 'p')
        if message is not None:
            for a in find_all(message, 'a'):
                href = a.get('href') or ''
                m = _WORKS_URL_RE.search(href)
                if m:
                    result['storyUrl'] = href.strip()
                    result['storyId'] = m.group(1)
                    break
            b = find_first(message, 'b')
            if b is not None:
                title_text = text_content(b).strip()
                if title_text:
                    result['title'] = title_text

        dl = find_first(preface, 'dl')
        if dl is not None:
            _parse_dl(dl, result)

        for key, value in result.items():
            download_result.setdefault(key, value)

    return download_result or None
