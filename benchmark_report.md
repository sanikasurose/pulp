# Pulp Benchmark Report

Deterministic format (no timestamps). Runtime varies by machine.

## Summary

- documents: 2
- total_pages: 4
- total_input: 2571 (2.5 KiB)
- total_input_tokens: 138
- total_output_tokens: 98
- token_reduction_pct: 29.0
- total_warnings: 1
- total_runtime_s: 0.639

## Per-document

| document | classification | page_count | input_bytes | input_tokens | output_tokens | token_reduction_pct | structure_accuracy | warnings | runtime_s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| simple_noise.pdf | TEXT_LAYER | 3 | 1557 | 78 | 37 | 52.6 | 100.0 | 1 | 0.620 |
| two_column.pdf | TEXT_LAYER | 1 | 1014 | 60 | 61 | -1.7 | 100.0 | 0 | 0.019 |

## Notes

- `structure_accuracy` is a deterministic snapshot similarity proxy when an expected Markdown file exists and `--llm` is disabled; it is not a semantic heading-accuracy score.
