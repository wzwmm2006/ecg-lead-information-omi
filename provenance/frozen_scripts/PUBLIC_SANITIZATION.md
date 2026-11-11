# Public sanitization record

The historical scripts preserve the analysis logic, but the public release removes machine-specific and private-service references.

| Item | Public treatment |
|---|---|
| Absolute Windows project path | Replaced by `<ROOT>` where present |
| Private evaluator endpoint/host | Replaced by `<EVALUATOR_ENDPOINT>` / `<EVALUATOR_HOST>` or generic naming |
| User-specific workspace path | Replaced by `<WORKSPACE>` |
| Patient data, waveform paths, model checkpoints | Not included |
| Patient identifiers | Not included |

The original-source fingerprints and the sanitized-file hashes are in `FROZEN_SCRIPT_SOURCE_FINGERPRINTS.json`. Sanitization changes the file byte hash; the original source hash is retained for audit.

No sensitive credential, patient record, institution-internal absolute path, or controlled dataset content is intentionally included.
