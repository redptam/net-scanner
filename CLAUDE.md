<!-- SPECKIT START -->
For this feature, the implementation plan is at specs/004-fix-filter-redraw-toggle/plan.md.
Key details:
- **Language**: Python 3.13, Tkinter
- **Bug location**: net_scanner_gui/main.py:282 _on_filter_unresponsive_toggle()
- **Fix**: Add self._detached_items set to track detached tree items; selectively reattach only hidden items on filter toggle off
- **Test**: net_scanner_gui/test_filter_toggle.py
<!-- SPECKIT END -->
