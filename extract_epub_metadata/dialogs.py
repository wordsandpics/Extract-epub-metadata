from qt.core import (
    QAbstractItemView, QComboBox, QDialog, QDialogButtonBox, QFormLayout,
    QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPlainTextEdit,
    QScrollArea, QSplitter, Qt, QVBoxLayout, QWidget,
)

from calibre_plugins.extract_epub_metadata.calibre_fields import (
    ALL_METADATA_KEYS, compatible_columns_for_key, field_help, field_label,
)
from calibre_plugins.extract_epub_metadata.anthology import format_summary, story_detail_lines
from calibre_plugins.extract_epub_metadata.extractors._text import html_to_text


def _format_field_dict(fields, sources=None):
    lines = []
    for key in sorted(fields):
        value = fields[key]
        if key in ('description', 'comments') and isinstance(value, str):
            value = html_to_text(value)
        if isinstance(value, list):
            value = '; '.join(str(v) for v in value)
        if sources is not None:
            lines.append('  %s [%s]: %s' % (key, sources.get(key, 'derived'), value))
        else:
            lines.append('  %s: %s' % (key, value))
    return lines


class BookResult:
    """One book's outcome from the extraction/mapping/serialization pipeline.
    `blob` and `standard_fields` are only populated for modes that are
    actually enabled for this run (empty/falsy otherwise), so
    summary_lines() only shows sections for what will actually happen."""

    def __init__(self, book_id, title, fields, sources, blob,
                 identifier_url=None, identifier_already_set=False,
                 existing_column_value=None, standard_fields=None,
                 custom_column_values=None, error=None, standard_skipped=None,
                 saved_write=None, notes=None, identifier_requested=True):
        self.book_id = book_id
        self.title = title
        self.fields = fields
        self.sources = sources
        self.blob = blob
        self.identifier_url = identifier_url
        self.identifier_already_set = identifier_already_set
        self.existing_column_value = existing_column_value
        self.standard_fields = standard_fields or {}
        self.custom_column_values = custom_column_values or {}
        self.error = error
        self.standard_skipped = standard_skipped or {}
        self.saved_write = bool(blob) if saved_write is None else saved_write
        self.notes = notes or []
        self.identifier_requested = identifier_requested
        self.write_errors = []
        self.written_fields = []

    @property
    def has_writes(self):
        return bool(not self.error and (self.saved_write or self.standard_fields or
                    self.custom_column_values or
                    (self.identifier_url and not self.identifier_already_set)))

    def summary_lines(self):
        if self.error:
            return ['Error: %s' % self.error]
        lines = list(self.notes)
        collection = self.fields.get('collectionType')
        if collection:
            lines.extend(['Collection: %s' % collection,
                          'Collection URL: %s' % self.fields.get('collectionUrl', 'not recovered'),
                          'Saved Metadata skipped: FanFicFare imports single stories, not collections.'])
        if self.identifier_url:
            note = ' (already set, not changed)' if self.identifier_already_set else ' (will be added)'
            lines.append('Story URL identifier: %s%s' % (self.identifier_url, note))
        elif not collection and self.identifier_requested:
            lines.append('Story URL identifier: not recovered -- FanFicFare '
                          'may not be able to pick an adapter for this book.')

        if self.standard_fields or self.standard_skipped:
            lines.append('')
            lines.append('=== Standard Calibre Fields ===')
            lines.extend(_format_field_dict(self.standard_fields))
            if self.standard_skipped:
                lines.append('Existing values kept; these fields will be skipped:')
                lines.extend(_format_field_dict(self.standard_skipped))

        if self.custom_column_values:
            lines.append('')
            lines.append('=== Custom Column Mapping ===')
            lines.extend(_format_field_dict(self.custom_column_values))

        if self.blob:
            lines.extend(['', '=== Saved Metadata Column ===',
                          'Will be written.' if self.saved_write else
                          'Existing column value kept; Saved Metadata will be skipped.'])
            lines.append('Recovered fields (source tier in brackets):')
            lines.extend(_format_field_dict(self.fields, self.sources))

        if collection:
            lines.extend(['', '=== Recovered Collection Facts ==='])
            lines.extend(_format_field_dict(
                {k: v for k, v in self.fields.items()
                 if k not in ('collectionRecords', 'collectionType')}, self.sources))
            records = self.fields.get('collectionRecords', [])
            if records:
                lines.extend(['', '=== Individual Stories ===', format_summary(records)])
                lines.extend(story_detail_lines(records))
            else:
                lines.append('Individual story metadata is not available in this EPUB.')
        if not self.has_writes:
            lines.extend(['', 'No changes will be written with the current settings.'])
            if collection:
                lines.append('Enable standard/custom-column updates, or use the anthology report '
                             'action for embedded story details.')

        return lines


class PreviewDialog(QDialog):
    """Summary of recovered metadata for one or more books, with a
    checkbox per book to include/exclude it from the write, shown before
    anything is actually written."""

    def __init__(self, gui, results):
        QDialog.__init__(self, gui)
        self.setWindowTitle('Extract Epub Metadata -- Preview')
        self.resize(760, 480)
        self.results = results

        layout = QVBoxLayout(self)

        intro = QLabel('Review metadata found in the book. Existing values are kept unless '
                       'overwriting is enabled. Skipped fields are labelled below. '
                       'Uncheck any book to skip it.')
        intro.setWordWrap(True)
        layout.addWidget(intro)

        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        layout.addWidget(splitter, 1)

        self.list_widget = QListWidget(splitter)
        self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        for result in results:
            item = QListWidgetItem(result.title or ('Book %s' % result.book_id))
            eligible = result.has_writes
            if eligible:
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if eligible else Qt.CheckState.Unchecked)
            item.setData(Qt.ItemDataRole.UserRole, result)
            if result.error:
                item.setToolTip(result.error)
            self.list_widget.addItem(item)
        self.list_widget.currentItemChanged.connect(self._show_details)

        self.details = QPlainTextEdit(splitter)
        self.details.setReadOnly(True)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText('Write Selected')
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.write_button = buttons.button(QDialogButtonBox.StandardButton.Ok)
        self.list_widget.itemChanged.connect(self._update_write_button)
        self._update_write_button()

        if self.list_widget.count():
            self.list_widget.setCurrentRow(0)

    def _show_details(self, current, _previous):
        if current is None:
            self.details.setPlainText('')
            return
        result = current.data(Qt.ItemDataRole.UserRole)
        self.details.setPlainText('\n'.join(result.summary_lines()))

    def _update_write_button(self, *_):
        self.write_button.setEnabled(bool(self.selected_results()))

    def selected_results(self):
        selected = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            result = item.data(Qt.ItemDataRole.UserRole)
            if item.checkState() == Qt.CheckState.Checked and result.has_writes:
                selected.append(result)
        return selected


class ColumnMappingDialog(QDialog):
    """Mode 3 config: one row per recoverable metadata field (as a static
    label, with a tooltip explaining it), each with a dropdown of the
    custom columns compatible with that field
    (calibre_fields.py::compatible_columns_for_key). Fields with no
    compatible column in this library aren't shown."""

    def __init__(self, gui, custom_columns, current_mapping, reserved_column=None):
        QDialog.__init__(self, gui)
        self.setWindowTitle('Extract Epub Metadata -- Custom Column Mapping')
        self.resize(600, 420)

        # current_mapping is {column_key: metadata_key} (matches how it's
        # stored/consumed elsewhere) -- invert it once for O(1) lookup of
        # "what column, if any, is this field currently mapped to".
        column_for_key = {v: k for k, v in current_mapping.items()}

        layout = QVBoxLayout(self)

        intro = QLabel(
            'Choose which column each extracted field should be written '
            'to. Empty or not mapped fields will be skipped. '
            'The Saved Metadata column is reserved for raw metadata.')
        intro.setWordWrap(True)
        layout.addWidget(intro)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        form_widget = QWidget(scroll)
        form = QFormLayout(form_widget)

        # The dropdown lists every column compatible by *datatype* alone
        # (calibre_fields.py::compatible_columns_for_key doesn't try to
        # guess semantic relevance), so e.g. a "chapters" text column
        # shows up as a candidate for "Category" too, not just "Chapters
        # (Downloaded/Total)" -- confusing without a clear header
        # distinguishing "this plugin's field" from "your column".
        header_field = QLabel('Extracted Field', form_widget)
        header_column = QLabel('Write To Column', form_widget)
        for header in (header_field, header_column):
            font = header.font()
            font.setBold(True)
            header.setFont(font)
        form.addRow(header_field, header_column)

        self.rows = []
        custom_columns = {k: v for k, v in custom_columns.items() if k != reserved_column}
        column_names = {key: col['name'] for key, col in custom_columns.items()}
        for metadata_key in sorted(ALL_METADATA_KEYS, key=field_label):
            column_keys = compatible_columns_for_key(metadata_key, custom_columns)
            if not column_keys:
                continue

            combo = QComboBox(form_widget)
            combo.addItem('(not mapped)', '')
            for column_key in sorted(column_keys, key=lambda ck: column_names[ck]):
                combo.addItem(column_names[column_key], column_key)
            idx = combo.findData(column_for_key.get(metadata_key, ''))
            combo.setCurrentIndex(idx if idx >= 0 else 0)

            label = QLabel(field_label(metadata_key) + ':', form_widget)
            help_text = field_help(metadata_key)
            if help_text:
                label.setToolTip(help_text)
                combo.setToolTip(help_text)

            form.addRow(label, combo)
            self.rows.append((metadata_key, combo))

        form_widget.setLayout(form)
        scroll.setWidget(form_widget)
        layout.addWidget(scroll, 1)

        if not self.rows:
            layout.addWidget(QLabel(
                'No custom columns with a supported datatype found. Create '
                'one in Preferences → Add your own columns first.'))

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def mapping(self):
        result = {}
        for metadata_key, combo in self.rows:
            column_key = combo.itemData(combo.currentIndex())
            if column_key:
                result[column_key] = metadata_key
        return result

    def accept(self):
        selected = [combo.currentData() for _, combo in self.rows if combo.currentData()]
        if len(selected) != len(set(selected)):
            from calibre.gui2 import error_dialog
            error_dialog(self, 'Conflicting mappings',
                         'Each destination column can receive only one extracted field. '
                         'Choose a different column for duplicate destinations.', show=True)
            return
        super().accept()
