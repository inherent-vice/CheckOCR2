## 2025-02-28 - Optimize Pandas DataFrame Iteration
**Learning:** `df.iterrows()` in Pandas is a massive performance bottleneck, especially when doing simple data extraction into native Python dictionaries. When iterating through rows, `df.iterrows()` wraps each row into a Series object, which causes significant overhead.
**Action:** Always prefer `df.to_dict('records')` over `df.iterrows()` when iterating over Pandas DataFrames in performance-sensitive paths, and don't forget to hoist loop-invariant lookups outside the loop.
