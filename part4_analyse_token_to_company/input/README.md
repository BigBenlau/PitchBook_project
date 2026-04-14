# Part4 Input

This folder stores immutable batch inputs for `part4_analyse_token_to_company`.

Expected layout:

- `batch_manifest.csv`
  - One row per batch.
- `batches/batch_0001.csv`
  - Batch input CSV.
- `batches/batch_0002.csv`
  - Batch input CSV.

Batch files should be treated as read-only once generated. Intermediate files must go to `../tmp/`, and final consolidated outputs must go to `../output/`.
