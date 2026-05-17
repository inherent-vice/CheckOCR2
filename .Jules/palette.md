## 2026-05-17 - Tkinter ToolTip bbox issue
**Learning:** Tkinter `Button` widgets do not support the `bbox` method. When calculating positioning for popups or tooltips on buttons, use `winfo_rootx()`, `winfo_rooty()`, and `winfo_height()` instead.
**Action:** When implementing ToolTip for Tkinter buttons, calculate coordinates based on `winfo_rootx()` and `winfo_rooty() + winfo_height()` to avoid `TclError: unknown option "-bbox"`.
