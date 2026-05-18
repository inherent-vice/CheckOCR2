## 2024-05-18 - ToolTip added to Tkinter Icon Button
**Learning:** In Tkinter applications, icon-only buttons lack inherent context, making them less accessible. Using a custom ToolTip class triggered by `<Enter>` and `<Leave>` events is an effective pattern for providing supplementary text, improving UX without cluttering the interface.
**Action:** When creating icon-only buttons in Tkinter, always pair them with a ToolTip to explain their function. Ensure mock UI widgets in the test suite have a `bind` method to support this pattern without breaking tests.
