"""Tests for _on_filter_unresponsive_toggle filter toggle fix."""

import tkinter as tk
from unittest.mock import MagicMock
import unittest

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from net_scanner_gui.main import NetworkScannerApp


def _make_mock_app(root):
    """Build a minimal mock app with the real toggle method bound."""
    app = object.__new__(NetworkScannerApp)
    mock_tree = MagicMock()
    # Pre-set get_children result; tests override as needed
    mock_tree.get_children.return_value = ["item1", "item2", "item3"]

    def item_side_effect(item_id, key=None):
        tags_map = {
            "item1": ("dead",),
            "item2": ("alive",),
            "item3": ("dead",),
        }
        tags = tags_map.get(item_id, ())
        if key is None:
            return {"tags": tags}
        return tags

    mock_tree.item.side_effect = item_side_effect
    mock_tree.reattach = MagicMock()
    mock_tree.detach = MagicMock()

    app.tree = mock_tree
    app.filter_unresponsive = tk.BooleanVar(root)
    app._detached_items = set()
    return app


class TestFilterToggle(unittest.TestCase):
    """Unit tests for the filter toggle fix."""

    def test_detach_on_filter_enable(self):
        """T004: Filter enable should detach items with 'dead' tag."""
        root = tk.Tk()
        root.withdraw()
        try:
            app = _make_mock_app(root)
            app.filter_unresponsive.set(False)
            app.filter_unresponsive.set(True)

            # Bind the real method
            toggle = NetworkScannerApp._on_filter_unresponsive_toggle.__get__(app)
            toggle()

            detach_calls = [c[0][0] for c in app.tree.detach.call_args_list]
            self.assertIn("item1", detach_calls)
            self.assertIn("item3", detach_calls)
            self.assertNotIn("item2", detach_calls)
            self.assertIn("item1", app._detached_items)
            self.assertIn("item3", app._detached_items)
        finally:
            root.destroy()

    def test_reattach_on_filter_disable(self):
        """T005: Filter disable should reattach only previously-detached items."""
        root = tk.Tk()
        root.withdraw()
        try:
            app = _make_mock_app(root)
            toggle = NetworkScannerApp._on_filter_unresponsive_toggle.__get__(app)

            app.filter_unresponsive.set(True)
            toggle()

            app.filter_unresponsive.set(False)
            toggle()

            reattach_calls = [c[0][0] for c in app.tree.reattach.call_args_list]
            self.assertIn("item1", reattach_calls)
            self.assertIn("item3", reattach_calls)
            self.assertNotIn("item2", reattach_calls)
            self.assertEqual(len(app._detached_items), 0)
        finally:
            root.destroy()

    def test_filter_with_no_results(self):
        """T006: Filter toggle with no tree items should be a no-op."""
        root = tk.Tk()
        root.withdraw()
        try:
            app = _make_mock_app(root)
            app.tree.get_children.return_value = []
            toggle = NetworkScannerApp._on_filter_unresponsive_toggle.__get__(app)

            app.filter_unresponsive.set(True)
            toggle()

            app.tree.detach.assert_not_called()
            app.tree.reattach.assert_not_called()
        finally:
            root.destroy()


if __name__ == "__main__":
    unittest.main()
