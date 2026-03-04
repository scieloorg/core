"""
Unit tests for the _format_code_sections method in ArticlemetaIssueFormatter.

These tests verify that the formatter correctly reads section data from
issue.table_of_contents (via TableOfContents -> JournalTableOfContents)
instead of the removed issue.code_sections attribute.
"""
from collections import defaultdict
from unittest.mock import MagicMock

from django.test import SimpleTestCase

from issue.formats.articlemeta_format import ArticlemetaIssueFormatter


def _make_formatter(toc_items):
    """
    Build a minimal ArticlemetaIssueFormatter without triggering __init__
    (which would require a database connection via Article.objects.filter).
    """
    formatter = object.__new__(ArticlemetaIssueFormatter)
    formatter.result = defaultdict(list)
    formatter.result["issue"] = {}

    mock_obj = MagicMock()
    mock_obj.table_of_contents.select_related.return_value.all.return_value = toc_items
    formatter.obj = mock_obj
    return formatter


def _make_toc_item(code=None, lang_code2=None, text=None):
    """
    Build a mock TableOfContents instance whose journal_toc has the given
    code, language.code2 and text values.
    """
    toc = MagicMock()
    journal_toc = MagicMock()
    journal_toc.code = code
    journal_toc.text = text
    if lang_code2 is not None:
        journal_toc.language.code2 = lang_code2
    else:
        journal_toc.language = None
    toc.journal_toc = journal_toc
    return toc


class TestFormatCodeSections(SimpleTestCase):
    def test_sections_with_code_language_and_text_are_formatted(self):
        """Sections with code, language and text produce the expected v49 entries."""
        toc_items = [
            _make_toc_item(code="SPM010", lang_code2="pt", text="Artigos originais"),
            _make_toc_item(code="SPM010", lang_code2="en", text="Original articles"),
        ]
        formatter = _make_formatter(toc_items)
        formatter._format_code_sections()

        v49 = formatter.result["issue"]["v49"]
        self.assertEqual(len(v49), 2)
        self.assertEqual(v49[0], {"c": "SPM010", "_": "", "l": "pt", "t": "Artigos originais"})
        self.assertEqual(v49[1], {"c": "SPM010", "_": "", "l": "en", "t": "Original articles"})

    def test_section_without_code_is_skipped(self):
        """A section whose journal_toc.code is None/empty must not appear in v49."""
        toc_items = [
            _make_toc_item(code=None, lang_code2="pt", text="Sem código"),
            _make_toc_item(code="ABC001", lang_code2="pt", text="Com código"),
        ]
        formatter = _make_formatter(toc_items)
        formatter._format_code_sections()

        v49 = formatter.result["issue"]["v49"]
        self.assertEqual(len(v49), 1)
        self.assertEqual(v49[0]["c"], "ABC001")

    def test_section_without_language_omits_l_key(self):
        """When language is None the 'l' key must be absent from the entry."""
        toc_items = [
            _make_toc_item(code="XYZ999", lang_code2=None, text="No language"),
        ]
        formatter = _make_formatter(toc_items)
        formatter._format_code_sections()

        v49 = formatter.result["issue"]["v49"]
        self.assertEqual(len(v49), 1)
        self.assertNotIn("l", v49[0])
        self.assertEqual(v49[0]["c"], "XYZ999")

    def test_section_without_text_omits_t_key(self):
        """When text is None/empty the 't' key must be absent from the entry."""
        toc_items = [
            _make_toc_item(code="XYZ001", lang_code2="en", text=None),
        ]
        formatter = _make_formatter(toc_items)
        formatter._format_code_sections()

        v49 = formatter.result["issue"]["v49"]
        self.assertEqual(len(v49), 1)
        self.assertNotIn("t", v49[0])

    def test_empty_table_of_contents_does_not_set_v49(self):
        """When there are no table_of_contents entries v49 must not be set."""
        formatter = _make_formatter([])
        formatter._format_code_sections()

        self.assertNotIn("v49", formatter.result["issue"])

    def test_all_sections_without_code_does_not_set_v49(self):
        """When every section lacks a code v49 must not appear."""
        toc_items = [
            _make_toc_item(code=None, lang_code2="pt", text="Sem código 1"),
            _make_toc_item(code=None, lang_code2="en", text="No code 2"),
        ]
        formatter = _make_formatter(toc_items)
        formatter._format_code_sections()

        self.assertNotIn("v49", formatter.result["issue"])

    def test_table_of_contents_is_queried(self):
        """The formatter must read from table_of_contents, not code_sections."""
        formatter = _make_formatter([])
        formatter._format_code_sections()

        formatter.obj.table_of_contents.select_related.assert_called_once_with("journal_toc__language")
        formatter.obj.table_of_contents.select_related.return_value.all.assert_called_once()
        # Confirm the old attribute (code_sections) was never called as a manager
        formatter.obj.code_sections.all.assert_not_called()
