"""
Story/series URL normalization shared across tiers.

Internet Archive Wayback Machine snapshots -- for fics recovered from an
archived snapshot rather than the live site (e.g. WebToEpub run against
web.archive.org -- confirmed against tests/fixtures/putting_up_shelves.epub,
whose OPF identifier, every dc:source, and the NCX uid are all the
snapshot URL, never the original AO3 one). A snapshot URL embeds the
original verbatim after a 14-digit timestamp and an optional two-letter
"flag" (im_, id_, if_, js_, cs_ ...):
    https://web.archive.org/web/20171212114900/https://archiveofourown.org/works/6173518
    https://web.archive.org/web/20210120042158im_/https://64.media.tumblr.com/...
Wayback also sometimes collapses the embedded scheme's '//' to a single
'/', or drops the scheme entirely -- both are normalized back.

AO3 host variants -- AO3's own older downloads (PDF especially) link to
http://download.archiveofourown.org/works/<id> (confirmed against
tests/fixtures/game_changer.epub), and old snapshots are often http:// or a
/chapters/... or ?view_full_work sub-page. All are canonicalized to
https://archiveofourown.org/works/<id> (series: /series/<id>) -- the same
shape AO3's current downloads carry, so FanFicFare's AO3 adapter and every
AO3-specific derivation here treat them identically.
"""
import re

_WAYBACK_RE = re.compile(
    r'^https?://(?:web\.|wayback\.)?archive\.org/web/\d{1,14}(?:[a-z]{2}_)?/+(.+)$', re.I)
_EMBEDDED_SCHEME_RE = re.compile(r'^(https?):/+', re.I)
_AO3_RE = re.compile(
    r'^https?://(?:www\.|download\.)?archiveofourown\.org/(works|series)/(\d+)', re.I)


def canonical_ao3_url(url):
    """https://archiveofourown.org/works/<id> (or /series/<id>) for any AO3
    work/series URL variant, or None if `url` isn't one. Doesn't unwrap
    Wayback URLs -- see unwrap_wayback_url()."""
    m = _AO3_RE.match((url or '').strip())
    if not m:
        return None
    return 'https://archiveofourown.org/%s/%s' % (m.group(1).lower(), m.group(2))


def unwrap_wayback_url(url):
    """Returns the original URL a Wayback snapshot URL points at, or None
    if `url` isn't a snapshot URL. AO3 work/series URLs are canonicalized
    (see canonical_ao3_url)."""
    if not url:
        return None
    m = _WAYBACK_RE.match(url.strip())
    if not m:
        return None
    original = m.group(1)
    if _EMBEDDED_SCHEME_RE.match(original):
        original = _EMBEDDED_SCHEME_RE.sub(lambda s: s.group(1).lower() + '://', original)
    else:
        original = 'https://' + original
    return canonical_ao3_url(original) or original


def is_wayback_url(url):
    return unwrap_wayback_url(url) is not None
