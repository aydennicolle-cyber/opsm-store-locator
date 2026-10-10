# Local use and protected sharing

Decision, 11 October 2026: the user authorised merging and pushing the current public-data application source to `main`. Public website deployment remains paused; the private companion and its research are outside this repository.

The GitHub Pages workflow no longer runs on pushes and deliberately fails before uploading any site artifact. This is a local source change, not a change to GitHub settings. The previously published site remains subject to its existing access settings until separately changed by an authorised user.

## Sharing through GitHub

A private repository can give invited collaborators access to source code, which they can run locally. Repository privacy does not automatically protect a GitHub Pages website. GitHub's private Pages access control requires an organisation on GitHub Enterprise Cloud and an eligible private or internal project repository.

Official reference: https://docs.github.com/en/enterprise-cloud%40latest/pages/getting-started-with-github-pages/changing-the-visibility-of-your-github-pages-site

The existing public-data repository must continue to exclude confidential leasing information. Do not add prospects, commercial terms or private decision notes to its files, history, build artifacts or public share URLs. Browser-local saved comparisons are not uploaded by the static-site deployment; a shared selection URL can disclose the locations it contains.

## If protected web hosting is requested later

Keep the static application architecture. Choose an authenticated hosting boundary, such as eligible private GitHub Pages or a separately configured access gateway, before re-enabling deployment. Keep confidential material in a separately controlled private environment rather than this public-data repository.

Verify access with both an authorised account and an unauthenticated session. The HTML, JSON, CSV, exports, alternate hostnames, preview deployments and any direct origin must all have the intended protection. A password form implemented only in client-side JavaScript cannot provide this protection. Avoid embedding passwords or access tokens in source code or URLs.

Retain the required data builds, application tests and public-privacy scan. Remove the publishing stop only as part of a reviewed, explicitly authorised protected deployment. Do not treat this document or the stop itself as evidence that authentication is enabled.
