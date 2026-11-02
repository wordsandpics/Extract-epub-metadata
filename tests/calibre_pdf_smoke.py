"""Direct PDF imports and independent write modes in an isolated Calibre library."""
import os
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
config = os.environ.get('CALIBRE_CONFIG_DIRECTORY')
if not config or not any(Path(config).resolve().is_relative_to(p.resolve()) for p in (Path('/private/tmp'), Path(tempfile.gettempdir()))):
    raise SystemExit('Use an explicit temporary CALIBRE_CONFIG_DIRECTORY.')
if sys.flags.optimize and not globals().get('_ASSERTIONS_ENABLED'):
    globals()['_ASSERTIONS_ENABLED'] = True
    exec(compile(Path(__file__).read_text(), __file__, 'exec', optimize=0))
    raise SystemExit(0)
from calibre.customize.ui import find_plugin
from calibre.ebooks.metadata.book.base import Metadata
from calibre.gui2 import Application
from calibre.library import db as open_library
from qt.core import QWidget
app=Application([])
ROOT=Path(__file__).resolve().parents[1]
plugin=find_plugin('Extract Epub Metadata')
assert plugin is not None
with plugin:
    from calibre_plugins.extract_epub_metadata.action import ExtractEpubMetadataAction
    from calibre_plugins.extract_epub_metadata.config import DEFAULT_STORE_VALUES, STORE_NAME, plugin_prefs
    from calibre_plugins.extract_epub_metadata.dialogs import PreviewDialog
    with tempfile.TemporaryDirectory(prefix='pdf-library-') as folder:
        db=open_library(folder)
        for label,kind in [('saved','comments'),('words','int')]:db.create_custom_column(label,label,kind,False)
        db.close();db=open_library(folder);api=db.new_api
        columns=api.field_metadata.custom_field_metadata()
        gui=QWidget();gui.current_db=db;gui.library_view=SimpleNamespace(model=lambda:SimpleNamespace(custom_columns=columns))
        action=ExtractEpubMetadataAction(gui,'')
        prefs=dict(DEFAULT_STORE_VALUES,destColumn='#saved',mode2Overwrite=True,columnMapping={'#words':'numWords'})
        plugin_prefs[STORE_NAME]=prefs
        def add(name,fmt='PDF'):
            bid=db.create_book_entry(Metadata('Before extraction',['Unknown']))
            with (ROOT/'tests/fixtures'/name).open('rb') as f:db.add_format(bid,fmt,f,index_is_id=True)
            return bid
        writes=0
        for name in ('pdf-ao3-table.pdf','pdf-ao3-stacked.pdf','pdf-ao3-older-notice.pdf','pdf-ao3-two-series.pdf'):
            for flags in ((True,False,False),(False,True,False),(False,False,True),(True,True,True)):
                bid=add(name)
                r=action._process_book(api,bid,'#saved',prefs,*flags,prefs['columnMapping'],columns)
                assert not r.error,r.error
                assert r.fields['numWords']==1234
                assert r.fields['author']==['TestWriterPDF']
                assert r.fields['authorUrl']==['https://archiveofourown.org/users/TestAccountPDF/pseuds/TestWriterPDF']
                assert r.fields['formatname']=='pdf'
                if 'two-series' in name:assert r.fields['series01']=='Other Synthetic Series [3]'
                assert action._write_results(api,'#saved',[r],*flags)==1
                assert bool(api.field_for('#saved',bid))==flags[0]
                assert (api.field_for('title',bid)!='Before extraction')==flags[1]
                assert (api.field_for('#words',bid)==1234)==flags[2]
                assert not r.write_errors,r.write_errors
                writes+=1
        import io
        from zipfile import ZipFile
        fff=find_plugin('FanFicFare')
        assert fff is not None
        with fff:
            from fanficfare import adapters, configurable
            from fanficfare.story import Story
            with ZipFile(fff.plugin_path) as archive:
                defaults=archive.read('plugin-defaults.ini').decode('utf-8')
            configuration=configurable.Configuration(adapters.getConfigSectionsFor(r.fields['storyUrl']),'epub')
            configuration.read_file(io.StringIO(defaults))
            story=Story(configuration);story.load_html_metadata(api.field_for('#saved',r.book_id))
            for key in ('title','author','authorUrl','numWords','numChapters','status','description','series'):
                if key in r.fields:assert story.metadata[key]==r.fields[key],key
        preview=PreviewDialog(gui,[r]);preview.show();app.processEvents();preview.close()
        for name in ('pdf-browser-unsupported.pdf','pdf-no-text.pdf'):
            r=action._process_book(api,add(name),'#saved',prefs,True,True,True,prefs['columnMapping'],columns)
            assert r.error and not r.fields,(name,r.fields)
        bid=add('pdf-ao3-table.pdf')
        with (ROOT/'tests/fixtures/txt-compact-complete.txt').open('rb') as f:db.add_format(bid,'TXT',f,index_is_id=True)
        r=action._process_book(api,bid,'#saved',prefs,False,True,True,prefs['columnMapping'],columns)
        assert r.fields['formatname']=='txt',r.error
        with (ROOT/'tests/fixtures/ao3-native-complete.epub').open('rb') as f:db.add_format(bid,'EPUB',f,index_is_id=True)
        r=action._process_book(api,bid,'#saved',prefs,False,True,True,prefs['columnMapping'],columns)
        assert r.fields['formatname']=='epub',r.error
        # A malformed preferred EPUB must not silently fall back to PDF/TXT.
        import io
        db.add_format(bid,'EPUB',io.BytesIO(b'not an epub'),index_is_id=True)
        r=action._process_book(api,bid,'#saved',prefs,False,True,True,prefs['columnMapping'],columns)
        assert r.error and not r.fields
        db.close()
        print('PASS: %d PDF write-mode cases, preview, unsupported/blank PDF rejection, EPUB > TXT > PDF, no fallback on malformed EPUB.'%writes)
