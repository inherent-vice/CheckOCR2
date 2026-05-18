## 2024-05-14 - Tooltip positioning for Tkinter Buttons
**Learning:** Tkinter `Button` widgets do not support the `bbox` method, causing exceptions if standard tooltip implementations try to use it for positioning.
**Action:** When calculating positioning for popups or tooltips on buttons, use `winfo_rootx()`, `winfo_rooty()`, and `winfo_height()` instead of `bbox()`.
