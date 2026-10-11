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

GitHub states Pages is not allowed as free hosting to run an online business. Since the intended site is ad supported, review https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits before using it commercially. The same files can be deployed to another static host without code changes. No repository, remote or production deployment has been created.

## Advertising

A reserved placement demonstrates layout without loading ad scripts. Actual monetization requires the user's publisher account, approved domain, actual privacy disclosures, any required consent flow and provider-provided ads.txt. Add scripts only after these are configured. Do not create a fabricated publisher ID or ads.txt entry.

## Features

Search names, numbers, teams and sections; accent-insensitive search; team/subset/rookie filters; product-specific odds; expandable family details; all-parallels odds view; pagination; sorting; filtered CSV exports; mobile layout; keyboard search shortcut and tab navigation. No personal collection data is stored.

## Data checks

`python3 scripts/verify_data.py` checks record grouping, source-page ranges, odds associations and key published values. Browser verification should cover searching, filter combinations, expanding details, switching pack format, pagination and CSV download.

`node scripts/verify_ui.mjs` exercises the application using lightweight DOM stubs. This verifies logic, not browser rendering. Browser automation was unavailable in the initial development session.
