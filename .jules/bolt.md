## 2024-05-18 - DataFrame Iteration in Pandas
**Learning:** Using `df.iterrows()` in Pandas is highly inefficient for data processing. Switching to `df.to_dict('records')` can provide nearly a 10x speedup in row iteration. Also, lookups inside the loop (e.g. `col_map.get()`) should be hoisted outside.
**Action:** Replace `df.iterrows()` with `df.to_dict('records')` when processing rows sequentially, and hoist loop-invariant variable lookups outside the loop.
