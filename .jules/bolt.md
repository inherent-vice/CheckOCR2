## 2024-05-13 - O(N) Grid Summarization
**Learning:** `summarize_grid_rows` in Tkinter table models used three separate list comprehensions (O(3N)) over UI state to count statuses instead of an O(N) single-pass iteration.
**Action:** When calculating multiple aggregates or summaries from lists, optimize to use a single pass to collect all metrics, particularly when those functions run often (like during UI grid refresh).
