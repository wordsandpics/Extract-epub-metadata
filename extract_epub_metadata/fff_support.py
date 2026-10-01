"""Optional offline check against an installed FanFicFare adapter registry."""
from .extractors.fallback_link_scan import _is_recognized_url
from .extractors._urls import is_wayback_url


def fff_support_url(identifiers, recovered_url, add_identifier):
    """Select the URL FFF will use after the planned identifier write.

    Existing url takes precedence over uri. A Wayback uri is bypassed only
    when this action will actually add the recovered original URL as url.
    """
    url = (identifiers.get('url') or '').replace('|', ':')
    uri = (identifiers.get('uri') or '').replace('|', ':')
    if url:
        return url
    if uri and not (is_wayback_url(uri) and add_identifier and recovered_url):
        return uri
    return recovered_url


def fff_import_support(url):
    """True/False when known; None when support cannot be checked.

    No FFF dependency is required for direct metadata/custom-column use.
    The registry lookup does not download the story or require a login.
    """
    if not url:
        return False
    try:
        from calibre.customize.ui import find_plugin
        plugin = find_plugin('FanFicFare')
        if plugin is not None:
            with plugin:
                from fanficfare import adapters
                from fanficfare.exceptions import UnknownSite
                try:
                    adapters.getConfigSectionsFor(url)
                except UnknownSite:
                    return False
                return True
    except (ImportError, AttributeError):
        pass
    # These two URL patterns are already supported by this plugin. Other
    # hosts are unverified, not automatically unsupported without FFF.
    return True if _is_recognized_url(url) else None
