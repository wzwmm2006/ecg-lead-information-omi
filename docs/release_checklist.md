# Release Checklist - v1.1.0

Status before publication: **RELEASE_CONDITIONAL**. This checklist governs creation of the v1.1.0 GitHub tag, GitHub Release, and Zenodo version. No GitHub tag, Release, or Zenodo version has been created in this work session.

## Candidate identity

- Repository branch: `release/v1.1.0`
- Base commit: `c0407059dc32585f14d56219ee1f2c2da344d1fb`
- Target version: `1.1.0`
- Candidate archive: `R2_V1_1_CANDIDATE_SOURCE.zip` (hash recorded in the project release record)

## Checks required before author approval

- [ ] Review `R2_V1_1_CODE_COVERAGE_MATRIX.md` and every `EXECUTABLE_VERIFIED` / `FROZEN_OUTPUT_MATCHED` / `PROVENANCE_ONLY` / `NOT_VERIFIED` classification.
- [ ] Review `R2_V1_1_CODE_AUDIT.md`, including the corrected class-weight finding (v1.0.0, frozen executor, and release agree exactly).
- [ ] Review the test output and frozen-output hash-verification output.
- [ ] Confirm no patient data, waveforms, model weights, row-level predictions, hidden labels, or local evaluator text are included.
- [ ] Confirm the title and all analysis distinctions match the R2 manuscript.
- [x] Historical release identity reconciled: `refs/tags/v1.0.0` resolves to commit `5b75a385b9c69d467005527f93c0f92aa78cd61a` remotely and locally; it was fetched, not created or moved. Commit `c040705` is a later metadata-only commit and must not be re-tagged.
- [ ] Verify the concept DOI `10.5281/zenodo.22046832` and the v1.0.0 version DOI `10.5281/zenodo.22046833` against the published records, and confirm the Zenodo integration status before creating a new version. Do not overwrite either record.
- [ ] Confirm the GitHub repository is public and code ownership/licensing consent is in place.
- [ ] Approve the release commit.

## Only after approval

- [x] Commit the source and metadata changes on `release/v1.1.0`.
- [x] Run the full data-free checks on the candidate commit (13 tests passed in the source tree and in the extracted archive).
- [ ] Fast-forward/merge into `main` under the owner's policy.
- [ ] Create an annotated tag `v1.1.0`. Do not reuse a tag.
- [ ] Push the commit and tag.
- [ ] Create a GitHub Release from the tag and attach the candidate archive.
- [ ] Verify that Zenodo GitHub integration exists and is enabled before publishing the GitHub Release.
- [ ] Prefer one archive path. If GitHub integration is active, do not also upload the same version manually.
- [ ] Record the GitHub tag SHA, release URL, and release-publication time.

## Post-publication verification

- [ ] Verify Zenodo version files, creator metadata, ORCID, license, title, version, and related data DOIs.
- [ ] Verify the newly minted version DOI resolves to the intended record.
- [ ] Verify that the concept DOI still resolves to the version chain.
- [ ] Download the archived ZIP and verify its SHA-256 and contents.
- [ ] Add the actual tag, DOI, archive hash, and verification result to `R2_V1_1_PUBLICATION_RECORD.md`.
- [ ] Only then use `RELEASE_PUBLISHED_VERIFIED`.

## Stop conditions

Stop and do not publish if any of the following is true:

- the source archive contains controlled data or identifiers;
- the archive contains an unverified claim of exact neural-network reproducibility;
- a DOI or version identity cannot be reconciled;
- the historical v1.0.0 release record would be overwritten;
- either GitHub or Zenodo produces a conflicting version of the same release;
- the author has not approved the final candidate.
