"""Run with calibre-debug in a temporary configuration with this plugin and FFF.

Imports only public synthetic examples into a temporary library. The configuration
guard and assertion recompilation below must remain before any Calibre imports.
"""
import io
import datetime
import itertools
import os
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from zipfile import ZipFile
config_dir = os.environ.get('CALIBRE_CONFIG_DIRECTORY')
scratch_roots = (Path('/private/tmp').resolve(), Path(tempfile.gettempdir()).resolve())
if not config_dir or not any((Path(config_dir).resolve().is_relative_to(root) for root in scratch_roots)):
    raise SystemExit('Refusing to run: CALIBRE_CONFIG_DIRECTORY must name a configuration in a temporary folder.')
if sys.flags.optimize and (not globals().get('_ASSERTIONS_ENABLED')):
    globals()['_ASSERTIONS_ENABLED'] = True
    exec(compile(Path(__file__).read_text(), __file__, 'exec', optimize=0))
    raise SystemExit(0)
from calibre.customize.ui import find_plugin
from calibre.ebooks.metadata.epub import get_metadata
from calibre.ebooks.metadata.book.base import Metadata
from calibre.gui2 import Application
from calibre.library import db as open_library
from qt.core import QWidget, Qt
from calibre.gui2.library.models import BooksModel
from calibre.utils.date import UNDEFINED_DATE, is_date_undefined
ROOT = Path(__file__).resolve().parents[1]
app = Application([])
plugin = find_plugin('Extract Epub Metadata')
assert plugin is not None, 'Install the plugin in the scratch configuration first.'
with plugin:
    from calibre_plugins.extract_epub_metadata.action import ExtractEpubMetadataAction
    from calibre_plugins.extract_epub_metadata.config import DEFAULT_STORE_VALUES, STORE_NAME, plugin_prefs, ConfigWidget
    from calibre_plugins.extract_epub_metadata.dialogs import PreviewDialog, _format_field_dict
    with tempfile.TemporaryDirectory(prefix='extract-metadata-library-') as library_path:
        db = open_library(library_path)
        for label, datatype in (('saved', 'comments'), ('report', 'comments'), ('words', 'int'), ('count', 'int'), ('unknown', 'int'), ('fandom', 'text'), ('updated', 'datetime')):
            db.create_custom_column(label, label.title(), datatype, False)
        db.close()
        db = open_library(library_path)
        api = db.new_api
        columns = api.field_metadata.custom_field_metadata()
        paths = [ROOT / 'tests/fixtures' / name for name in ['ao3-information-thin-space.epub', 'ao3-series-collection.epub', 'ao3-information-ongoing.epub', 'anthology-outer-status-tag.epub', 'ao3-browser-space-counts.epub', 'titlepage-paragraph-ffnet.epub', 'anthology-complete.epub', 'ao3-native-ongoing.epub', 'titlepage-unicode.epub', 'ao3-series-navigation.epub', 'fichub-ao3-introduction.epub', 'fichub-ao3-completed.epub', 'fichub-ao3-summary-entities.epub', 'pdf-labelled-header.epub', 'titlepage-ongoing.epub']]
        paths.extend((ROOT / 'tests/fixtures' / n for n in ('anthology-multiple-authors.epub', 'ao3-anonymous-singular-tags.epub', 'titlepage-paragraph-summary.epub', 'ao3-split-coauthors.epub', 'ao3-pdf-wrapped-preface.epub')))
        ids = []
        for path in paths:
            with path.open('rb') as f:
                mi = get_metadata(f, extract_cover=False)
            book_id = db.create_book_entry(mi)
            with path.open('rb') as f:
                db.add_format(book_id, 'EPUB', f, index_is_id=True)
            ids.append(book_id)
        prefs = dict(DEFAULT_STORE_VALUES, destColumn='#saved', mode2Enabled=True, mode3Enabled=True, anthologyDestColumn='#report', columnMapping={'#words': 'numWords', '#count': 'collectionStoryCount', '#unknown': 'collectionUnknownCount'})
        plugin_prefs[STORE_NAME] = prefs
        gui = QWidget()
        gui.current_db = db
        refresh_calls, tag_recounts = ([], [])
        library_model = SimpleNamespace(custom_columns=columns, refresh_ids=lambda ids, row: refresh_calls.append((list(ids), row)))
        gui.library_view = SimpleNamespace(model=lambda: library_model, currentIndex=lambda: SimpleNamespace(row=lambda: 0))
        gui.tags_view = SimpleNamespace(recount=lambda: tag_recounts.append(True))
        action = ExtractEpubMetadataAction(gui, '')
        results = [action._process_book(api, book_id, '#saved', prefs, True, True, True, prefs['columnMapping'], columns) for book_id in ids]
        assert not [r.error for r in results if r.error], [r.error for r in results if r.error]
        collections = [r for r in results if r.fields.get('collectionType')]
        assert len(collections) == 4
        for r in collections:
            assert not r.blob and (not r.identifier_url)
            assert r.standard_skipped
        count = action._write_results(api, '#saved', results, True, True, True)
        assert count == sum((bool(r.written_fields) for r in results))
        unsupported = [r for r in results if not r.fields.get('collectionType') and (not r.blob)]
        for r in unsupported:
            assert not api.field_for('#saved', r.book_id)
            assert any(('Saved Metadata skipped' in line for line in r.summary_lines()))
        assert action._write_results(api, '#saved', results, True, True, True) == 0
        for r in collections:
            assert not api.field_for('#saved', r.book_id)
            assert api.field_for('#count', r.book_id) == r.fields['collectionStoryCount']
        good = next((r for r in collections if r.fields['collectionStoryCount'] == 5))
        assert api.field_for('#words', good.book_id) == 93149
        assert api.field_for('#unknown', good.book_id) == 0
        report = action._process_anthology_book(api, good.book_id, '#report')
        assert report.has_writes and 'TestWriter15' in report.summary
        assert action._write_anthology_results(api, '#report', [report], False) == 1
        assert action._write_anthology_results(api, '#report', [report], False) == 0
        expected = {'ao3-series-collection.epub': {'numWords': 11822, 'collectionStoryCount': 2}, 'ao3-information-thin-space.epub': {'numWords': 111536}, 'anthology-multiple-authors.epub': {'numWords': 93149, 'collectionChapterCount': 66}, 'ao3-split-coauthors.epub': {'author': ['TestWriter02', 'TestWriter03'], 'numWords': 17674}, 'ao3-anonymous-singular-tags.epub': {'author': ['Anonymous'], 'authorHTML': 'Anonymous'}}
        for path, r in zip(paths, results):
            for key, value in expected.get(path.name, {}).items():
                assert r.fields[key] == value, (path.name, key)
            if path.name == 'ao3-series-navigation.epub':
                assert r.fields['series'] == 'TestSeries06 [1]'
                assert r.fields['seriesUrl'] == 'https://archiveofourown.org/series/98000436'
            if path.name == 'ao3-anonymous-singular-tags.epub':
                assert 'authorUrl' not in r.fields and 'authorId' not in r.fields
        assert _format_field_dict({'comments': '<p>A &amp; B</p><p>Next</p>'}) == ['  comments: A & B\n\nNext']
        config = ConfigWidget(action)
        assert config.validate() and config.validate_before_accept
        assert config.anthology_dest_column.findData('#saved') == -1
        config.column_mapping['#saved'] = 'description'
        config._refresh_saved_columns()
        assert config.dest_column.findData('#saved') == -1
        assert config.saved_column_note.text()
        assert config.validate()
        del config.column_mapping['#saved']
        config._refresh_saved_columns()
        config.dest_column.setCurrentIndex(config.dest_column.findData('#saved'))
        config._refresh_report_columns()
        preview = PreviewDialog(gui, results)
        screenshots = os.environ.get('EXTRACT_METADATA_SCREENSHOTS')
        if screenshots:
            from calibre.constants import __version__
            folder = Path(screenshots)
            folder.mkdir(parents=True, exist_ok=True)
            config.resize(680, 700)
            config.show()
            app.processEvents()
            assert config.grab().save(str(folder / ('config-%s.png' % __version__)))
            config.hide()
            preview.show()
            app.processEvents()
            assert preview.grab().save(str(folder / ('preview-%s.png' % __version__)))
            preview.hide()
        eligible = preview.selected_results()
        for i in range(preview.list_widget.count()):
            preview.list_widget.item(i).setCheckState(Qt.CheckState.Unchecked)
        assert not preview.selected_results() and (not preview.write_button.isEnabled())
        if eligible:
            for i in range(preview.list_widget.count()):
                item = preview.list_widget.item(i)
                if item.data(Qt.ItemDataRole.UserRole) is eligible[0]:
                    item.setCheckState(Qt.CheckState.Checked)
                    break
            assert preview.selected_results() == [eligible[0]]
        preview.close()
        mode1_only = action._process_book(api, good.book_id, '', prefs, True, False, False, {}, columns)
        assert not mode1_only.error and (not mode1_only.has_writes)
        no_write_preview = PreviewDialog(gui, [mode1_only])
        assert not no_write_preview.write_button.isEnabled()
        no_write_preview.close()

        class FailingDB:

            def __getattr__(self, name):
                return getattr(api, name)

            def set_field(self, name, values):
                if name == '#words' and good.book_id in values:
                    raise RuntimeError('simulated write failure')
                return api.set_field(name, values)
        prefs['mode2Overwrite'] = True
        plugin_prefs[STORE_NAME] = prefs
        good.standard_fields = {'title': 'Scratch partial update'}
        later = next((r for r in results if not r.fields.get('collectionType')))
        later.standard_fields = {'title': 'Scratch later book'}
        assert action._write_results(FailingDB(), '#saved', [good, later], False, True, True) == 2
        assert good.write_errors and good.written_fields == ['title']
        assert not later.write_errors
        assert api.field_for('title', later.book_id) == 'Scratch later book'
        import calibre_plugins.extract_epub_metadata.action as action_module
        messages = []
        original_error_dialog = action_module.error_dialog
        action_module.error_dialog = lambda *a, **k: messages.append(k.get('det_msg', ''))
        try:
            action._show_outcome([good, later], 2, 2, False)
        finally:
            action_module.error_dialog = original_error_dialog
        assert 'Changed fields: title' in messages[0]
        assert 'simulated write failure' in messages[0]
        fff = find_plugin('FanFicFare')
        assert fff is not None
        with fff:
            from fanficfare import adapters, configurable
            from fanficfare.story import Story
            with ZipFile(fff.plugin_path) as archive:
                defaults = archive.read('plugin-defaults.ini').decode('utf-8')
            round_trips = 0
            skipped = []
            for r in results:
                if r.fields.get('collectionType'):
                    continue
                url = r.fields.get('storyUrl')
                if not r.blob:
                    skipped.append(r.title)
                    continue
                configuration = configurable.Configuration(adapters.getConfigSectionsFor(url), 'epub')
                configuration.read_file(io.StringIO(defaults))
                story = Story(configuration)
                story.load_html_metadata(api.field_for('#saved', r.book_id))
                for key in ('title', 'author', 'authorUrl', 'numWords', 'numChapters', 'status', 'series', 'rating', 'storyUrl', 'description'):
                    if key in r.fields:
                        assert story.metadata.get(key) == r.fields[key], (r.title, key, story.metadata.get(key), r.fields[key])
                story.getSubjectTags()
                round_trips += 1
        generic_path = ROOT / 'tests/fixtures/opf-only-no-markers.epub'
        with generic_path.open('rb') as f:
            generic_id = db.create_book_entry(get_metadata(f, extract_cover=False))
        with generic_path.open('rb') as f:
            db.add_format(generic_id, 'EPUB', f, index_is_id=True)
        lj = next((r for r in results if 'livejournal.com' in (r.fields.get('storyUrl') or '')))
        work_url = 'https://archiveofourown.org/works/123'
        encoded = work_url.replace(':', '|')
        for bid in (generic_id, lj.book_id):
            api.set_field('identifiers', {bid: {'url': encoded}})
            r = action._process_book(api, bid, '#saved', prefs, True, False, False, {}, columns)
            assert not r.error and r.blob and r.saved_write
            assert not any(('Saved Metadata skipped' in n for n in r.notes))
            assert action._write_results(api, '#saved', [r], True, False, False) == 1
            assert api.field_for('identifiers', bid) == {'url': encoded}
        api.set_field('identifiers', {lj.book_id: {}})
        lj_without_id = action._process_book(api, lj.book_id, '#saved', prefs, True, False, False, {}, columns)
        assert not lj_without_id.error and (not lj_without_id.blob)
        supported = next((r for r in results if r.fields.get('storyUrl', '').startswith('https://archiveofourown.org/works/')))
        for identifiers, add, should_save in (({'uri': 'https|//example.com/unsupported'}, True, False), ({'uri': 'https|//web.archive.org/web/20200101/' + supported.fields['storyUrl']}, True, True), ({'uri': 'https|//web.archive.org/web/20200101/' + supported.fields['storyUrl']}, False, False)):
            api.set_field('identifiers', {supported.book_id: identifiers})
            p = dict(prefs, addMissingIdentifier=add)
            r = action._process_book(api, supported.book_id, '#saved', p, True, False, False, {}, columns)
            assert not r.error and bool(r.blob) == should_save, (identifiers, add, r.error, r.notes)
        import calibre_plugins.extract_epub_metadata.action as action_module
        matrix_ids = ids
        gui.library_view.get_selected_ids = lambda: matrix_ids
        baseline_columns = ('title', 'authors', 'tags', 'comments', 'series', 'pubdate', 'languages', 'identifiers', '#saved', '#words', '#count', '#unknown')

        def snapshot():
            return {bid: tuple((api.field_for(col, bid) for col in baseline_columns)) for bid in matrix_ids}
        outcomes = []
        original_outcome = action._show_outcome
        action._show_outcome = lambda rs, count, *a, **kw: outcomes.append((rs, count))

        class AcceptedPreview(PreviewDialog):

            def exec(self):
                for i in range(self.list_widget.count()):
                    item = self.list_widget.item(i)
                    if item.data(Qt.ItemDataRole.UserRole).has_writes:
                        item.setCheckState(Qt.CheckState.Unchecked)
                        break
                return self.DialogCode.Accepted
        original_preview = action_module.PreviewDialog
        action_module.PreviewDialog = AcceptedPreview
        cases = 0
        try:
            for modes in itertools.product((False, True), repeat=3):
                if not any(modes):
                    continue
                for saved_overwrite, std_overwrite, show_preview, add_identifier in itertools.product((False, True), repeat=4):
                    for col, value in (('title', 'Keep title'), ('authors', ['Keep author']), ('tags', ['Keep tag']), ('comments', '<p>Keep comments</p>'), ('series', 'Keep series'), ('pubdate', UNDEFINED_DATE), ('languages', ['fr']), ('identifiers', {}), ('#saved', 'Keep saved'), ('#words', None), ('#count', None), ('#unknown', None)):
                        api.set_field(col, {bid: value for bid in matrix_ids})
                    matrix_prefs = dict(prefs, mode1Enabled=modes[0], mode2Enabled=modes[1], mode3Enabled=modes[2], overwrite=saved_overwrite, mode2Overwrite=std_overwrite, preview=show_preview, addMissingIdentifier=add_identifier)
                    plugin_prefs[STORE_NAME] = matrix_prefs
                    before = snapshot()
                    outcomes.clear()
                    refresh_calls.clear()
                    tag_recounts.clear()
                    action.run()
                    assert len(outcomes) == 1
                    rs, changed_count = outcomes[0]
                    changed_ids = [r.book_id for r in rs if r.written_fields]
                    assert refresh_calls == ([(changed_ids, 0)] if changed_ids else [])
                    assert len(tag_recounts) == bool(changed_ids)
                    assert not [r.error or r.write_errors for r in rs if r.error or r.write_errors]
                    after = snapshot()
                    assert changed_count == sum((before[bid] != after[bid] for bid in matrix_ids))
                    excluded = next((r for r in rs if r.has_writes), None) if show_preview else None
                    for r in rs:
                        bid = r.book_id
                        if excluded is r:
                            assert before[bid] == after[bid]
                            continue
                        if not modes[0] or not saved_overwrite or (not r.blob):
                            assert api.field_for('#saved', bid) == 'Keep saved'
                        if not modes[1] or not std_overwrite:
                            assert api.field_for('title', bid) == 'Keep title'
                            assert api.field_for('authors', bid) == ('Keep author',)
                        elif r.fields.get('title'):
                            assert api.field_for('title', bid) == r.fields['title']
                        if modes[1] and r.fields.get('datePublished'):
                            assert not is_date_undefined(api.field_for('pubdate', bid))
                        elif not modes[1]:
                            assert is_date_undefined(api.field_for('pubdate', bid))
                        if modes[2] and 'numWords' in r.fields:
                            assert api.field_for('#words', bid) == r.fields['numWords']
                        elif not modes[2]:
                            assert api.field_for('#words', bid) is None
                        if not add_identifier or r.fields.get('collectionType'):
                            assert not api.field_for('identifiers', bid)
                    cases += 1
        finally:
            action_module.PreviewDialog = original_preview
            action._show_outcome = original_outcome
        api.set_field('authors', {ids[-1]: ['Unknown']})
        api.set_field('pubdate', {ids[-1]: UNDEFINED_DATE})
        plugin_prefs[STORE_NAME] = dict(prefs, mode2Overwrite=False)
        blank = action._process_book(api, ids[-1], '#saved', dict(prefs, mode2Overwrite=False), False, True, False, {}, columns)
        assert {'authors', 'pubdate'} <= set(blank.standard_fields)
        action._write_results(api, '#saved', [blank], False, True, False)
        assert api.field_for('authors', ids[-1]) == ('TestWriter12',)
        assert api.field_for('pubdate', ids[-1]).date().isoformat() == '2016-12-21'
        confirmations = []
        original_info = action_module.info_dialog
        action_module.info_dialog = lambda *a, **kw: confirmations.append(a[2])
        try:
            plugin_prefs[STORE_NAME] = dict(prefs, mode1Enabled=True, mode2Enabled=False, mode3Enabled=False, preview=False, addMissingIdentifier=False)
            matrix_ids = [good.book_id]
            action.run()
            assert 'Collections do not receive' in confirmations[-1]
            # Use the explicit unsupported source, independent of scenario ordering.
            api.set_field('identifiers', {lj.book_id: {}})
            matrix_ids = [lj.book_id]
            action.run()
            assert 'Saved Metadata skipped' in confirmations[-1], confirmations[-1]
        finally:
            action_module.info_dialog = original_info
        txt_cases = [('txt-compact-complete.txt', 'Synthetic TXT Compact Complete', 459, 'en'), ('txt-compact-packaged-date.txt', 'Synthetic TXT Compact Packaged Date', 66818, 'en'), ('txt-compact-missing-url.txt', 'Synthetic TXT Compact Missing URL', 26036, 'en'), ('txt-compact-spanish-ongoing.txt', 'Synthetic TXT Compact Spanish Ongoing', 2196, 'es'), ('txt-compact-spanish-complete.txt', 'Synthetic TXT Compact Spanish Complete — Café', 3740, 'es')]
        txt_prefs = dict(prefs, mode2Overwrite=True)
        plugin_prefs[STORE_NAME] = txt_prefs
        txt_results = []
        for name, title, words, language in txt_cases:
            bid = db.create_book_entry(Metadata('Archive placeholder', ['Unknown']))
            with (ROOT / 'tests/fixtures' / name).open('rb') as stream:
                db.add_format(bid, 'TXT', stream, index_is_id=True)
            r = action._process_book(api, bid, '#saved', txt_prefs, True, True, True, prefs['columnMapping'], columns)
            assert not r.error, r.error
            assert r.fields['formatname'] == 'txt' and r.sources['title'] == 'txt_header'
            assert r.fields['title'] == title and r.fields['numWords'] == words
            if name.startswith('txt-compact-missing-url'):
                assert not r.blob and (not r.identifier_url)
                assert any(('Saved Metadata skipped' in note for note in r.notes))
                mode1 = action._process_book(api, bid, '#saved', txt_prefs, True, False, False, {}, columns)
                assert not mode1.error and (not mode1.has_writes)
            else:
                assert r.blob and r.identifier_url
            txt_results.append(r)
        txt_preview = PreviewDialog(gui, txt_results)
        assert len(txt_preview.selected_results()) == 5
        if screenshots:
            txt_preview.show()
            app.processEvents()
            assert txt_preview.grab().save(str(folder / 'txt-preview.png'))
            txt_preview.hide()
        txt_preview.close()
        assert action._write_results(api, '#saved', txt_results, True, True, True) == 5
        with fff:
            for (name, title, words, language), r in zip(txt_cases, txt_results):
                bid = r.book_id
                assert api.field_for('title', bid) == title
                assert api.field_for('authors', bid) == tuple(r.fields['author'])
                assert api.field_for('#words', bid) == words
                assert api.field_for('languages', bid) == ({'en': 'eng', 'es': 'spa'}[language],)
                assert r.fields['category'][0] in api.field_for('tags', bid)
                assert api.field_for('pubdate', bid).date() == r.fields['datePublished'].date()
                assert api.field_for('comments', bid)
                if r.blob:
                    configuration = configurable.Configuration(adapters.getConfigSectionsFor(r.fields['storyUrl']), 'txt')
                    configuration.read_file(io.StringIO(defaults))
                    story = Story(configuration)
                    story.load_html_metadata(api.field_for('#saved', bid))
                    for key in ('title', 'author', 'authorUrl', 'numWords', 'numChapters', 'status', 'rating', 'storyUrl', 'description', 'formatname', 'datePublished'):
                        assert story.metadata[key] == r.fields[key], (name, key)
                    assert api.field_for('identifiers', bid)['url'] == r.fields['storyUrl'].replace(':', '|')
                else:
                    assert not api.field_for('#saved', bid)
                    api.set_field('identifiers', {bid: {'url': 'https|//www.fanfiction.net/s/98000700/1/'}})
                    with_url = action._process_book(api, bid, '#saved', txt_prefs, True, False, False, {}, columns)
                    assert not with_url.error and with_url.blob and with_url.saved_write
        both = txt_results[0].book_id
        with generic_path.open('rb') as stream:
            epub_title = get_metadata(stream, extract_cover=False).title
        with generic_path.open('rb') as stream:
            db.add_format(both, 'EPUB', stream, index_is_id=True)
        preferred = action._process_book(api, both, '#saved', txt_prefs, False, True, False, {}, columns)
        assert not preferred.error and preferred.fields['title'] == epub_title
        assert preferred.fields['formatname'] == 'epub'
        assert 'txt_header' not in preferred.sources.values()
        missing = db.create_book_entry(Metadata('No supported format'))
        missing_result = action._process_book(api, missing, '#saved', txt_prefs, True, False, False, {}, columns)
        assert 'No EPUB or TXT format' in missing_result.error and (not missing_result.has_writes)
        db.add_format(missing, 'TXT', io.BytesIO(b'Ordinary story text without metadata'), index_is_id=True)
        missing_result = action._process_book(api, missing, '#saved', txt_prefs, True, False, False, {}, columns)
        assert 'No recognizable opening metadata header' in missing_result.error and (not missing_result.has_writes)
        variant_cases = [('txt-pdf-detached-partial', 'Synthetic TXT PDF Detached Partial', 857, 'txt_pdf_partial', None), ('txt-pdf-squidgeworld', 'Synthetic TXT PDF Squidgeworld', 1422, 'txt_pdf_preface', 'TestFandom15'), ('txt-spaced-missing-url', 'Synthetic TXT Spaced Missing URL', 373, 'txt_spaced_header', 'TestFandom13'), ('txt-spaced-wrapped-tags', 'Synthetic TXT Spaced Wrapped Tags', 799, 'txt_spaced_header', 'TestFandom13'), ('txt-spaced-multiple-fandoms', 'Synthetic TXT Spaced Multiple Fandoms', 565, 'txt_spaced_header', 'TestFandom14, TestFandom13')]
        variant_mapping = {'#words': 'numWords', '#fandom': 'fandoms'}
        variant_results = []
        for prefix, title, words, source, fandom in variant_cases:
            path = next((p for p in (ROOT / 'tests/fixtures').iterdir() if p.name.startswith(prefix)))
            bid = db.create_book_entry(Metadata(title + ' (scratch import)', ['Keep existing author']))
            api.set_field('#fandom', {bid: 'Keep existing fandom'})
            with path.open('rb') as stream:
                db.add_format(bid, 'TXT', stream, index_is_id=True)
            r = action._process_book(api, bid, '#saved', txt_prefs, True, True, True, variant_mapping, columns)
            assert not r.error, r.error
            assert r.fields['title'] == title and r.fields['numWords'] == words
            assert r.sources['title'] == source
            if source == 'txt_pdf_partial':
                assert any(('Partial TXT recovery' in note for note in r.notes))
                assert 'authors' not in r.standard_fields and '#fandom' not in r.custom_column_values
            assert bool(r.blob) == bool(r.fields.get('storyUrl')), r.notes
            variant_results.append(r)
        variant_preview = PreviewDialog(gui, variant_results)
        assert len(variant_preview.selected_results()) == 5
        if screenshots:
            variant_preview.show()
            app.processEvents()
            assert variant_preview.grab().save(str(folder / 'txt-variants-preview.png'))
            variant_preview.hide()
        variant_preview.close()
        assert action._write_results(api, '#saved', variant_results, True, True, True) == 5
        with fff:
            for (prefix, title, words, source, fandom), r in zip(variant_cases, variant_results):
                bid = r.book_id
                assert api.field_for('title', bid) == title
                assert api.field_for('#words', bid) == words
                if fandom is None:
                    assert api.field_for('#fandom', bid) == 'Keep existing fandom'
                    assert api.field_for('authors', bid) == ('Keep existing author',)
                else:
                    assert api.field_for('#fandom', bid) == fandom
                    assert api.field_for('authors', bid) == tuple(r.fields['author'])
                if r.blob:
                    configuration = configurable.Configuration(adapters.getConfigSectionsFor(r.fields['storyUrl']), 'txt')
                    configuration.read_file(io.StringIO(defaults))
                    story = Story(configuration)
                    story.load_html_metadata(api.field_for('#saved', bid))
                    for key in ('title', 'author', 'numWords', 'status', 'storyUrl', 'description', 'datePublished', 'ao3categories', 'fandoms', 'series'):
                        if key in r.fields:
                            assert story.metadata[key] == r.fields[key], (prefix, key)
        ficlab_cases = [('ficlab-multichapter-count-priority.epub', 101933, 23, '2012-02-01T05:34:56+00:00'), ('ficlab-timestamp-day-boundary.epub', 4054, 1, '2012-12-29T23:59:29+00:00'), ('ficlab-rating-k-plus.epub', 5661, 1, '2012-01-01T05:30:09+00:00'), ('ficlab-mixed-tags.epub', 2944, 1, '2010-08-17T15:51:19+00:00')]
        ficlab_mapping = {'#words': 'numWords', '#updated': 'dateUpdated', '#fandom': 'fandoms'}
        ficlab_results = []
        for name, words, chapters, published in ficlab_cases:
            path = ROOT / 'tests/fixtures' / name
            with path.open('rb') as stream:
                bid = db.create_book_entry(get_metadata(stream, extract_cover=False))
            with path.open('rb') as stream:
                db.add_format(bid, 'EPUB', stream, index_is_id=True)
            api.set_field('title', {bid: name.removesuffix('.epub')})
            api.set_field('#fandom', {bid: 'Keep uncategorized fandom'})
            keep = action._process_book(api, bid, '#saved', dict(prefs, mode2Overwrite=False), True, True, True, ficlab_mapping, columns)
            assert not keep.error and 'title' in keep.standard_skipped
            r = action._process_book(api, bid, '#saved', txt_prefs, True, True, True, ficlab_mapping, columns)
            assert not r.error, r.error
            assert r.fields['numWords'] == words and r.fields['numChapters'] == chapters
            assert r.fields['datePublished'].isoformat() == published
            assert r.sources['numWords'] == 'ficlab_summary'
            assert r.fields['datePublished'].utcoffset().total_seconds() == 0
            assert '#fandom' not in r.custom_column_values
            assert r.blob and r.saved_write
            ficlab_results.append(r)
        ficlab_preview = PreviewDialog(gui, ficlab_results)
        assert len(ficlab_preview.selected_results()) == 4
        if screenshots:
            ficlab_preview.show()
            app.processEvents()
            assert ficlab_preview.grab().save(str(folder / 'ficlab-preview.png'))
            ficlab_preview.hide()
        ficlab_preview.close()
        assert action._write_results(api, '#saved', ficlab_results, True, True, True) == 4
        with fff:
            for (name, words, chapters, published), r in zip(ficlab_cases, ficlab_results):
                bid = r.book_id
                assert not r.write_errors, r.write_errors
                assert api.field_for('#words', bid) == words
                assert api.field_for('#fandom', bid) == 'Keep uncategorized fandom'
                assert api.field_for('title', bid) == r.fields['title']
                assert api.field_for('pubdate', bid).isoformat() == published
                assert api.field_for('#updated', bid) == r.fields['dateUpdated']
                assert set(r.fields['extratags']) <= set(api.field_for('tags', bid))
                configuration = configurable.Configuration(adapters.getConfigSectionsFor(r.fields['storyUrl']), 'epub')
                configuration.read_file(io.StringIO(defaults))
                story = Story(configuration)
                story.load_html_metadata(api.field_for('#saved', bid))
                for key in ('title', 'author', 'authorId', 'authorUrl', 'numWords', 'numChapters', 'status', 'rating', 'extratags', 'datePublished', 'dateUpdated'):
                    expected_value = r.fields[key]
                    if key in ('datePublished', 'dateUpdated'):
                        assert story.metadata[key + 'SourceTimestamp'] == expected_value.isoformat()
                        expected_value = expected_value.astimezone(datetime.timezone.utc).replace(tzinfo=None)
                    assert story.metadata[key] == expected_value, (name, key, story.metadata[key], expected_value)
                story.getSubjectTags()
        visible_bid = ficlab_results[0].book_id
        api.set_field('title', {visible_bid: 'Before extraction'})
        api.set_field('#words', {visible_bid: None})
        api.set_field('#count', {visible_bid: None})
        qt_model = BooksModel(gui)
        qt_model.set_database(db)
        visible_row = db.data.id_to_index(visible_bid)
        title_index = qt_model.index(visible_row, qt_model.column_map.index('title'))
        words_index = qt_model.index(visible_row, qt_model.column_map.index('#words'))
        chapters_index = qt_model.index(visible_row, qt_model.column_map.index('#count'))
        assert qt_model.data(title_index, Qt.ItemDataRole.DisplayRole) == 'Before extraction'
        assert not qt_model.data(words_index, Qt.ItemDataRole.DisplayRole)
        assert not qt_model.data(chapters_index, Qt.ItemDataRole.DisplayRole)
        repaint_events, detail_events = ([], [])
        qt_model.dataChanged.connect(lambda first, last, *args: repaint_events.append((first.row(), last.row())))
        qt_model.new_bookdisplay_data.connect(detail_events.append)
        gui.library_view = SimpleNamespace(model=lambda: qt_model, currentIndex=lambda: title_index, get_selected_ids=lambda: [visible_bid])
        plugin_prefs[STORE_NAME] = dict(txt_prefs, overwrite=True, preview=False, columnMapping={'#words': 'numWords', '#count': 'numChapters'})
        previous_outcome = action._show_outcome
        action._show_outcome = lambda *args, **kwargs: None
        try:
            action.run()
            assert repaint_events and detail_events
            assert qt_model.data(title_index, Qt.ItemDataRole.DisplayRole) == 'Synthetic FicLab Multichapter Count Priority'
            assert str(qt_model.data(words_index, Qt.ItemDataRole.DisplayRole)).replace(',', '') == '101933'
            assert str(qt_model.data(chapters_index, Qt.ItemDataRole.DisplayRole)) == '23'
            assert detail_events[-1].get('#words') == 101933
            assert detail_events[-1].get('#count') == 23
        finally:
            action._show_outcome = previous_outcome
            qt_model.stop_metadata_backup()
        print('PASS: all three modes refresh the real Qt book list and book details; standard/custom values visible without FFF.')
        print('PASS: 4 FicLab previews/writes/FFF round trips, summary word counts, aware dates and uncategorized tags.')
        print('PASS: 5 TXT variant previews/writes, 2 FFF round trips including SquidgeWorld, partial-recovery notes, preserved omitted columns.')
        print('PASS: 5 TXT previews and Calibre writes, 4 TXT FFF round trips, missing URLs, EPUB priority, unrecognized files.')
        db.close()
        print('PASS: %d fresh imports, %d collections, %d FFF multi-key round trips, %d run() matrix cases.' % (len(paths), len(collections), round_trips, cases))
        print('PASS: preview unchecking, independent overwrite flags, placeholder writes, anthology report, partial failures.')
        print('Skipped unsupported FFF imports (%d): %s' % (len(skipped), '; '.join(skipped)))
