"""Run with calibre-debug and a separate CALIBRE_CONFIG_DIRECTORY.

Install this plugin and FanFicFare in that configuration first. The script
creates a temporary library, imports real fixture EPUBs, and never opens
the user's library. QT_QPA_PLATFORM=offscreen avoids displaying windows.
"""
import io
import itertools
import os
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from zipfile import ZipFile

# Some Calibre launchers enable Python optimization, which otherwise
# removes every assert in this script. Compile the verification code with
# assertions enabled before importing or exercising the plugin.
if sys.flags.optimize and not globals().get('_ASSERTIONS_ENABLED'):
    globals()['_ASSERTIONS_ENABLED'] = True
    exec(compile(Path(__file__).read_text(), __file__, 'exec', optimize=0))
    raise SystemExit(0)

from calibre.customize.ui import find_plugin
from calibre.ebooks.metadata.epub import get_metadata
from calibre.gui2 import Application
from calibre.library import db as open_library
from qt.core import QWidget, Qt
from calibre.utils.date import UNDEFINED_DATE, is_date_undefined

ROOT = Path(__file__).resolve().parents[1]
app = Application([])
plugin = find_plugin('Extract Epub Metadata')
assert plugin is not None, 'Install the plugin in the scratch configuration first.'
with plugin:
    from calibre_plugins.extract_epub_metadata.action import ExtractEpubMetadataAction
    from calibre_plugins.extract_epub_metadata.config import (
        DEFAULT_STORE_VALUES, STORE_NAME, plugin_prefs, ConfigWidget,
    )
    from calibre_plugins.extract_epub_metadata.dialogs import PreviewDialog, _format_field_dict

    with tempfile.TemporaryDirectory(prefix='extract-metadata-library-') as library_path:
        db = open_library(library_path)
        for label, datatype in (('saved', 'comments'), ('report', 'comments'),
                                ('words', 'int'), ('count', 'int'), ('unknown', 'int')):
            db.create_custom_column(label, label.title(), datatype, False)
        db.close()
        db = open_library(library_path)
        api = db.new_api
        columns = api.field_metadata.custom_field_metadata()
        paths = sorted((ROOT / 'tests/fixtures/all new').glob('*.epub'))
        paths.extend(ROOT / 'tests/fixtures' / n for n in (
            'anthology_a_good_man_and_an_angry_man.epub', 'we_could_be_something.epub',
            'sigh_no_more.epub', 'two_weddings_and_a_funeral.epub', 'game_changer.epub'))
        ids = []
        for path in paths:
            with path.open('rb') as f:
                mi = get_metadata(f, extract_cover=False)
            book_id = db.create_book_entry(mi)
            with path.open('rb') as f:
                db.add_format(book_id, 'EPUB', f, index_is_id=True)
            ids.append(book_id)
        prefs = dict(DEFAULT_STORE_VALUES, destColumn='#saved', mode2Enabled=True,
                     mode3Enabled=True, anthologyDestColumn='#report',
                     columnMapping={'#words': 'numWords', '#count': 'collectionStoryCount',
                                    '#unknown': 'collectionUnknownCount'})
        plugin_prefs[STORE_NAME] = prefs
        gui = QWidget()
        gui.current_db = db
        gui.library_view = SimpleNamespace(model=lambda: SimpleNamespace(custom_columns=columns))
        action = ExtractEpubMetadataAction(gui, '')
        results = [action._process_book(api, book_id, '#saved', prefs, True, True, True,
                                       prefs['columnMapping'], columns) for book_id in ids]
        assert not [r.error for r in results if r.error], [r.error for r in results if r.error]
        collections = [r for r in results if r.fields.get('collectionType')]
        assert len(collections) == 4
        for r in collections:
            assert not r.blob and not r.identifier_url
            assert r.standard_skipped  # fresh Calibre import already read the outer fields
        count = action._write_results(api, '#saved', results, True, True, True)
        assert count == sum(bool(r.written_fields) for r in results)
        unsupported = [r for r in results if not r.fields.get('collectionType') and not r.blob]
        for r in unsupported:
            assert not api.field_for('#saved', r.book_id)
            assert any('Saved Metadata skipped' in line for line in r.summary_lines())
        assert action._write_results(api, '#saved', results, True, True, True) == 0
        for r in collections:
            assert not api.field_for('#saved', r.book_id)
            assert api.field_for('#count', r.book_id) == r.fields['collectionStoryCount']
        good = next(r for r in collections if r.fields['collectionStoryCount'] == 5)
        assert api.field_for('#words', good.book_id) == 93149
        assert api.field_for('#unknown', good.book_id) == 0
        report = action._process_anthology_book(api, good.book_id, '#report')
        assert report.has_writes and 'Myst1248' in report.summary
        assert action._write_anthology_results(api, '#report', [report], False) == 1
        assert action._write_anthology_results(api, '#report', [report], False) == 0

        # Independent expectations taken from the real fixture prefaces.
        expected = {
            'Breaking_Point.epub': {'numWords': 11822, 'collectionStoryCount': 2},
            'A_Matter...rmanence.epub': {'numWords': 111536},
            'anthology_a_good_man_and_an_angry_man.epub': {'numWords': 93149, 'collectionChapterCount': 66},
            'two_weddings_and_a_funeral.epub': {'author': ['fabricdragon', 'SpeculativeCorvid'], 'numWords': 17674},
            'we_could_be_something.epub': {'author': ['Anonymous'], 'authorHTML': 'Anonymous'},
        }
        for path, r in zip(paths, results):
            for key, value in expected.get(path.name, {}).items():
                assert r.fields[key] == value, (path.name, key)
            if path.name.startswith('The Shrunken Jumper'):
                assert r.fields['series'] == 'Everyday life in 221b [1]'
                assert r.fields['seriesUrl'] == 'https://archiveofourown.org/series/60213'
            if path.name == 'we_could_be_something.epub':
                assert 'authorUrl' not in r.fields and 'authorId' not in r.fields

        # Instantiate the actual Qt configuration and preview against scratch data.
        assert _format_field_dict({'comments': '<p>A &amp; B</p><p>Next</p>'}) == ['  comments: A & B\n\nNext']
        config = ConfigWidget(action)
        assert config.validate() and config.validate_before_accept
        assert config.anthology_dest_column.findData('#saved') == -1
        config.column_mapping['#saved'] = 'description'
        config._refresh_saved_columns()
        assert config.dest_column.findData('#saved') == -1
        assert config.saved_column_note.text()
        assert config.validate()  # old conflicts cannot close/discard other edits
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
        assert not preview.selected_results() and not preview.write_button.isEnabled()
        if eligible:
            for i in range(preview.list_widget.count()):
                item = preview.list_widget.item(i)
                if item.data(Qt.ItemDataRole.UserRole) is eligible[0]:
                    item.setCheckState(Qt.CheckState.Checked)
                    break
            assert preview.selected_results() == [eligible[0]]
        preview.close()
        mode1_only = action._process_book(api, good.book_id, '', prefs, True, False, False, {}, columns)
        assert not mode1_only.error and not mode1_only.has_writes
        no_write_preview = PreviewDialog(gui, [mode1_only])
        assert not no_write_preview.write_button.isEnabled()
        no_write_preview.close()

        # A later field failing must retain partial progress and allow the next book.
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
        later = next(r for r in results if not r.fields.get('collectionType'))
        later.standard_fields = {'title': 'Scratch later book'}
        assert action._write_results(FailingDB(), '#saved', [good, later], False, True, True) == 2
        assert good.write_errors and good.written_fields == ['title']
        assert not later.write_errors
        assert api.field_for('title', later.book_id) == 'Scratch later book'
        # Verify the reporter names partial changes without opening a modal.
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

        # FFF reads actual database blobs, not values copied out of a rich-text editor.
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
                for key in ('title', 'author', 'authorUrl', 'numWords', 'numChapters',
                            'status', 'series', 'rating', 'storyUrl', 'description'):
                    if key in r.fields:
                        assert story.metadata.get(key) == r.fields[key], (r.title, key, story.metadata.get(key), r.fields[key])
                story.getSubjectTags()
                round_trips += 1
        # Existing identifiers take precedence over EPUB links in FFF (follow-up R1).
        generic_path = ROOT / 'tests/fixtures/generic_no_markers.epub'
        with generic_path.open('rb') as f:
            generic_id = db.create_book_entry(get_metadata(f, extract_cover=False))
        with generic_path.open('rb') as f:
            db.add_format(generic_id, 'EPUB', f, index_is_id=True)
        lj = next(r for r in results if 'livejournal.com' in (r.fields.get('storyUrl') or ''))
        work_url = 'https://archiveofourown.org/works/123'
        encoded = work_url.replace(':', '|')
        for bid in (generic_id, lj.book_id):
            api.set_field('identifiers', {bid: {'url': encoded}})
            r = action._process_book(api, bid, '#saved', prefs, True, False, False, {}, columns)
            assert not r.error and r.blob and r.saved_write
            assert not any('Saved Metadata skipped' in n for n in r.notes)
            assert action._write_results(api, '#saved', [r], True, False, False) == 1
            assert api.field_for('identifiers', bid) == {'url': encoded}
        api.set_field('identifiers', {lj.book_id: {}})
        lj_without_id = action._process_book(api, lj.book_id, '#saved', prefs, True, False, False, {}, columns)
        assert not lj_without_id.error and not lj_without_id.blob
        supported = next(r for r in results if r.fields.get('storyUrl', '').startswith('https://archiveofourown.org/works/'))
        for identifiers, add, should_save in (
            ({'uri': 'https|//example.com/unsupported'}, True, False),
            ({'uri': 'https|//web.archive.org/web/20200101/' + supported.fields['storyUrl']}, True, True),
            ({'uri': 'https|//web.archive.org/web/20200101/' + supported.fields['storyUrl']}, False, False),
        ):
            api.set_field('identifiers', {supported.book_id: identifiers})
            p = dict(prefs, addMissingIdentifier=add)
            r = action._process_book(api, supported.book_id, '#saved', p, True, False, False, {}, columns)
            assert not r.error and bool(r.blob) == should_save, (identifiers, add, r.error, r.notes)

        # All mode combinations through run(), with the two overwrite options independent.
        import calibre_plugins.extract_epub_metadata.action as action_module
        matrix_ids = ids
        gui.library_view.get_selected_ids = lambda: matrix_ids
        baseline_columns = ('title', 'authors', 'tags', 'comments', 'series', 'pubdate',
                            'languages', 'identifiers', '#saved', '#words', '#count', '#unknown')
        def snapshot():
            return {bid: tuple(api.field_for(col, bid) for col in baseline_columns) for bid in matrix_ids}
        outcomes = []
        original_outcome = action._show_outcome
        action._show_outcome = lambda rs, count, *a, **kw: outcomes.append((rs, count))
        class AcceptedPreview(PreviewDialog):
            def exec(self):
                # Exercise real preview selection: exclude the first eligible book.
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
                    for col, value in (('title', 'Keep title'), ('authors', ['Keep author']),
                                       ('tags', ['Keep tag']), ('comments', '<p>Keep comments</p>'),
                                       ('series', 'Keep series'), ('pubdate', UNDEFINED_DATE),
                                       ('languages', ['fr']), ('identifiers', {}),
                                       ('#saved', 'Keep saved'), ('#words', None), ('#count', None), ('#unknown', None)):
                        api.set_field(col, {bid: value for bid in matrix_ids})
                    matrix_prefs = dict(prefs, mode1Enabled=modes[0], mode2Enabled=modes[1],
                                        mode3Enabled=modes[2], overwrite=saved_overwrite,
                                        mode2Overwrite=std_overwrite, preview=show_preview,
                                        addMissingIdentifier=add_identifier)
                    plugin_prefs[STORE_NAME] = matrix_prefs
                    before = snapshot()
                    outcomes.clear()
                    action.run()
                    assert len(outcomes) == 1
                    rs, changed_count = outcomes[0]
                    assert not [r.error or r.write_errors for r in rs if r.error or r.write_errors]
                    after = snapshot()
                    assert changed_count == sum(before[bid] != after[bid] for bid in matrix_ids)
                    excluded = next((r for r in rs if r.has_writes), None) if show_preview else None
                    for r in rs:
                        bid = r.book_id
                        if excluded is r:
                            assert before[bid] == after[bid]
                            continue
                        if not modes[0] or not saved_overwrite or not r.blob:
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
        # Real placeholder author/date writes with overwrite disabled.
        api.set_field('authors', {ids[-1]: ['Unknown']})
        api.set_field('pubdate', {ids[-1]: UNDEFINED_DATE})
        plugin_prefs[STORE_NAME] = dict(prefs, mode2Overwrite=False)
        blank = action._process_book(api, ids[-1], '#saved', dict(prefs, mode2Overwrite=False),
                                     False, True, False, {}, columns)
        assert {'authors', 'pubdate'} <= set(blank.standard_fields)
        action._write_results(api, '#saved', [blank], False, True, False)
        assert api.field_for('authors', ids[-1]) == ('EloiseReed',)
        assert api.field_for('pubdate', ids[-1]).date().isoformat() == '2016-12-21'
        # Preview-off skipped runs still explain why nothing was written.
        confirmations = []
        original_info = action_module.info_dialog
        action_module.info_dialog = lambda *a, **kw: confirmations.append(a[2])
        try:
            plugin_prefs[STORE_NAME] = dict(prefs, mode1Enabled=True, mode2Enabled=False,
                mode3Enabled=False, preview=False, addMissingIdentifier=False)
            matrix_ids = [good.book_id]
            action.run()
            assert 'Collections do not receive' in confirmations[-1]
            matrix_ids = [unsupported[0].book_id]
            action.run()
            assert 'Saved Metadata skipped' in confirmations[-1]
        finally:
            action_module.info_dialog = original_info
        db.close()
        print('PASS: %d fresh imports, %d collections, %d FFF multi-key round trips, %d run() matrix cases.' %
              (len(paths), len(collections), round_trips, cases))
        print('PASS: preview unchecking, independent overwrite flags, placeholder writes, anthology report, partial failures.')
        print('Skipped unsupported FFF imports (%d): %s' % (len(skipped), '; '.join(skipped)))
