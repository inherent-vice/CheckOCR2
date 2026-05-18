## 2024-05-12 - Added Tooltips to Tkinter
**Learning:** Tkinter doesn't have native tooltips. A custom tooltip class is required to provide hover hints for icon-only buttons like the "📂" folder open button. This is a common accessibility gap in Tkinter apps.
**Action:** Created a reusable `Tooltip` class in `checkocr2/ui/tooltip.py` and applied it to the `open_folder_btn` and other icon buttons.
