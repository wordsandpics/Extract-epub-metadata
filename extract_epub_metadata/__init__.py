from calibre.customize import InterfaceActionBase

__version__ = (1, 1, 0)


class ExtractEpubMetadataBase(InterfaceActionBase):
    """
    Wrapper plugin class. The real GUI logic lives in action.py's
    ExtractEpubMetadataAction, loaded lazily so calibredb/CLI usage
    doesn't need to import Qt.
    """

    name = 'Extract Epub Metadata'
    description = (
        'Recover metadata from fanfiction EPUBs or TXT archive headers already in Calibre; save it '
        'for FanFicFare or write standard and custom fields.'
    )
    supported_platforms = ['windows', 'osx', 'linux']
    author = 'wordsandpics'
    version = __version__
    minimum_calibre_version = (6, 0, 0)

    actual_plugin = 'calibre_plugins.extract_epub_metadata.action:ExtractEpubMetadataAction'

    def is_customizable(self):
        return True

    def config_widget(self):
        from calibre_plugins.extract_epub_metadata.config import ConfigWidget
        return ConfigWidget(self.actual_plugin_)

    def save_settings(self, config_widget):
        config_widget.save_settings()
