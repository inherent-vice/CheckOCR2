## 2024-05-16 - Tooltips for Tkinter Buttons Without Bbox
**Learning:** Tkinter `Button` widgets do not support the `bbox` method. Attempting to use `bbox` to position tooltips or popups relative to a button will fail or cause unexpected layout issues.
**Action:** Always use `winfo_rootx()`, `winfo_rooty()`, and `winfo_height()` instead of `bbox` to calculate placement for popups and tooltips connected to Tkinter `Button` widgets.
