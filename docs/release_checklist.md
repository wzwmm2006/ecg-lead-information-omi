# GitHub and Zenodo Release Checklist

## GitHub

- Replace `OWNER` in `CITATION.cff` with the final GitHub organization or username.
- Replace DOI placeholders after identifiers are reserved or assigned.
- Review the public tree and source manifest one final time.
- Confirm that `data/`, `outputs/`, `models/`, `logs/`, archives, and Python caches are ignored and absent.
- Create the public GitHub repository with the same repository name.
- Commit the reviewed allowlisted files.
- Add the remote and push the default branch.
- Create annotated tag `v1.0.0` and a GitHub release using `RELEASE_NOTES.md`.
- Attach the prepared ZIP and checksum if a standalone archive is desired in addition to Zenodo's GitHub snapshot.

## Zenodo

- Sign in to Zenodo and enable the GitHub repository under GitHub integration.
- Confirm the creators, affiliations, title, description, software type, MIT license, keywords, related dataset DOIs, and version against `.zenodo.json`.
- Publish the GitHub `v1.0.0` release to trigger archival, or upload the prepared ZIP to a reserved Zenodo draft.
- Verify that the deposited archive contains no controlled data and matches the local SHA-256 checksum.
- Record the version DOI and concept DOI.
- Replace `10.5281/zenodo.TBD` in `CITATION.cff` with the assigned software DOI.
- Replace `ARTICLE_DOI_TBD` after the Scientific Reports DOI is assigned.
- Update the GitHub repository description and README citation details without altering the archived v1.0.0 contents.
