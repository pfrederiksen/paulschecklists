# Paul's Checklists

A buildless, static sports-card reference site. The first release covers the official 2026 Topps Allen & Ginter Baseball checklist and all 97 entries in its odds sheet.

## Preview

Run `python3 -m http.server 8000` from this directory, then visit http://localhost:8000. No npm installation or build is needed. Opening index.html directly will not load JSON in most browsers.

## Data provenance

The official product page is https://www.topps.com/pages/topps-allen-ginter-baseball. Exact checklist and odds PDF URLs and SHA-256 hashes are retained in `data/allen-ginter-2026.json`. Original PDFs are in `data/sources/`. Verified October 11, 2026.

Install pdfplumber and run `python3 scripts/import_checklist.py` to reproduce the dataset from the retained PDFs. Extraction fails on unrecognized lines; it checks the 300-card base numbering and 97 odds entries. Family mappings are explicit aliases in the importer. Multiple subjects sharing a code are grouped within a section, preserving each original source line and page.

Odds are category-level per-pack values by fat pack, hobby and value box. No specific-subject odds, serial numbering, print runs or universal parallel eligibility are inferred. Topps' spelling is preserved in data, including “FILAGREE.” Mini exclusives and Career 250 have no matching published odds entry. The two framed mini relic sections share the combined published category odds. Base full-size cards have no published base odds; their associated parallels remain available. A source dash means not listed for that format, not impossible.

## Hosting

All paths are relative and work on a project subpath, including GitHub Pages. For a prototype, publish the repository root from a branch in Settings → Pages. No backend is needed.

GitHub states Pages is not allowed as free hosting to run an online business. Since the intended site is ad supported, review https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits before using it commercially. The same files can be deployed to another static host without code changes. Repository: https://github.com/pfrederiksen/paulschecklists

Live site: https://pfrederiksen.github.io/paulschecklists/

GitHub Pages publishes the `docs/` directory on `main`. Run `node scripts/build_site.mjs`, commit the source and generated `docs/` files, then push to publish changes.

## Advertising

AdSense Auto ads integration is present but disabled; no ad scripts are loaded until configured. Actual monetization requires the user's publisher account, approved domain, actual privacy disclosures, any required consent flow and provider-provided ads.txt. Add scripts only after these are configured. Do not create a fabricated publisher ID or ads.txt entry.

## Features

Search names, numbers, teams and sections; accent-insensitive search; team/subset/rookie filters; product-specific odds; expandable family details; all-parallels odds view; pagination; sorting; filtered CSV exports; mobile layout; keyboard search shortcut and tab navigation. No personal collection data is stored.

## Data checks

`python3 scripts/verify_data.py` checks record grouping, source-page ranges, odds associations and key published values. Browser verification should cover searching, filter combinations, expanding details, switching pack format, pagination and CSV download.

`node scripts/verify_ui.mjs` exercises the application using lightweight DOM stubs. This verifies logic, not browser rendering. Browser automation was unavailable in the initial development session.

## AdSense activation

`ads-config.js` contains public publisher configuration. The integration is disabled and contains no invented publisher IDs. Before activation, configure the actual publisher ID (Auto ads do not require an ad-slot ID), add this site to AdSense for review, publish the required privacy disclosures, and configure Google's certified consent message or another certified CMP. See https://support.google.com/adsense/answer/7584263 and https://support.google.com/adsense/answer/13554116.

The build generates `docs/ads.txt` only when a real publisher ID is present. For the current project URL, that file is below the domain root; it must also be deployed at https://pfrederiksen.github.io/ads.txt (through the root-site repository) or served at the root of a custom domain assigned to this project. No root-site changes have been made.

Auto ads settings are controlled in AdSense → Ads → site settings. Turn on Auto ads there after approval. Setup instructions: https://support.google.com/adsense/answer/9261307. The shared loader is included on both the checklist and privacy pages; manual ad units and reserved placements have been removed.

## Custom-domain path deployment

The canonical checklist address is https://paulfrederiksen.com/checklists/. The domain is served by the separate `pfrederiksen/paulfrederiksen.com` Astro repository. After building, run `node scripts/sync_domain_site.mjs /path/to/domain-repository` to copy generated assets to its `public/checklists/` directory and merge the real publisher record into `public/ads.txt`. Commit and push that repository to publish the domain version. Its photography homepage is preserved. The original project Pages URL remains available.

Publisher ID: `ca-pub-6005669570779380`. Verification metadata and the ads.txt seller record are configured. Auto ads serving is enabled following user confirmation of approval and consent setup. No ad-slot ID is needed.

Auto ads enabled October 11, 2026. Google controls placement and whether an ad is served. No reserved ad block or manual ad units remain.

## Set directory and Bowman Football

`/checklists/` is now the landing directory. Set pages are `allen-ginter-2026.html` and `bowman-football-2026.html`; the latter uses the official 34-page checklist and nine-page odds PDF, covering 47 sections, 2,122 grouped entries and 521 odds rows across Hobby, FDI, Breaker, Jumbo, Mega and Value. Rebuild its data with `python3 scripts/import_bowman.py` (pdfplumber required). Run `node scripts/verify_bowman.mjs` for dataset and application checks.

The Bowman source repeats NFL base #68 and omits #66. Both entries remain separate, preserving the source error. Multi-subject autograph codes are grouped. Some odds cells are blank, preserved as unpublished.

All public checklist pages reuse the exact GoatCounter account configured in the domain repository's `src/layouts/BaseLayout.astro`: `https://paulfrederiksen.goatcounter.com/count`, with the `https://gc.zgo.at/count.js` script. Analytics disclosure is in the shared privacy page. No separate analytics account is introduced.
