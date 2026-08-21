# GitHub and Zenodo Release Checklist

## GitHub

- Confirm that `CITATION.cff` uses the final GitHub repository URL.
- Do not add a software or article DOI until the identifier has been assigned.
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
- Add the assigned version DOI to `CITATION.cff` after Zenodo archives the software release.
- Add the Scientific Reports citation only after the article is published and its bibliographic metadata are final.
- Update the GitHub repository description and README citation details without altering the archived v1.0.0 contents.
