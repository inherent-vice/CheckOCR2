## 2025-02-24 - Pandas iterrows optimization
**Learning:** Iterating over Pandas DataFrames using `df.iterrows()` in performance-sensitive paths like grid loading creates high overhead due to Series object instantiation for every row.
**Action:** Always prefer `df.to_dict('records')` over `df.iterrows()` for iterating rows, as plain dictionary lookups are significantly faster. Additionally, hoist loop-invariant dictionary `.get()` lookups out of loops to avoid redundant function calls.
