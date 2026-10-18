# Public publishing and private-data boundary

Decision, 18 October 2026: the user explicitly authorised re-enabling the public GitHub Pages site after confirming that it is publicly accessible. This replaces the 11 October publishing pause. The private companion, BN commercial data, local study overlays and private reports remain outside this repository and deployment.

The GitHub Pages workflow runs on pushes to `main` or manual dispatch. It rebuilds the public datasets, runs the application tests and privacy scan, and uploads only the static website files: `index.html`, assets, public data, retailer pages, public census downloads and `.nojekyll`. A generated `deployment.json` identifies the deployed commit. Repository scripts, local output folders and sibling private workspaces are not part of the site artifact.

## Sharing through GitHub

A private repository can give invited collaborators access to source code, which they can run locally. Repository privacy does not automatically protect a GitHub Pages website. GitHub's private Pages access control requires an organisation on GitHub Enterprise Cloud and an eligible private or internal project repository.

Official reference: https://docs.github.com/en/enterprise-cloud%40latest/pages/getting-started-with-github-pages/changing-the-visibility-of-your-github-pages-site

The existing public-data repository must continue to exclude confidential leasing information. Do not add prospects, commercial terms or private decision notes to its files, history, build artifacts or public share URLs. Browser-local saved comparisons are not uploaded by the static-site deployment; a shared selection URL can disclose the locations it contains.

## If protected web hosting is requested later

Keep the static application architecture. Choose an authenticated hosting boundary, such as eligible private GitHub Pages or a separately configured access gateway, before sharing confidential material through any future hosted application. Keep confidential material in a separately controlled private environment rather than this public-data repository.

Verify access with both an authorised account and an unauthenticated session. The HTML, JSON, CSV, exports, alternate hostnames, preview deployments and any direct origin must all have the intended protection. A password form implemented only in client-side JavaScript cannot provide this protection. Avoid embedding passwords or access tokens in source code or URLs.

Retain the required data builds, application tests and public-privacy scan. The current website is public; neither repository visibility nor a client-side login screen provides access protection. Any later change to a protected deployment requires explicit authorisation and access checks.
