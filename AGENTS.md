# Checklist experience

The first Allen & Ginter page defines the experience for every set. All set pages must be generated with `templates/set-page.mjs` through `node scripts/generate_source_pages.mjs`; do not create separate page shells or manufacturer-specific navigation layouts. Featured content lives in `templates/featured-sets.json`.

Keep the same header, hero, statistics, insights, Cards / Parallels & pack odds tabs, search, subset/team/pack-format filters, rookie control, sorting, reset, CSV export, card family details, family odds tables, pagination, and source explanation. Disable controls with unavailable source fields rather than changing their position. Keep manufacturer-specific published specifications inside these shared views. Preserve official columns in expanded card details. Do not invent teams, rookie flags, pack formats, category odds, print runs, or parallel eligibility.

For new sets and source updates, run `node scripts/verify_set_template.mjs`, `node scripts/verify_source_pages.mjs`, `node scripts/verify_ui.mjs`, `node scripts/verify_bowman.mjs`, and `node scripts/verify_catalog.mjs` after generating/building. Add new data through adapters and the shared template rather than introducing a new visual or interaction format.

# Checklist SEO

Keep metadata and crawlable checklist content in `templates/seo.mjs`, applied through the shared generator. `scripts/build_site.mjs` publishes the full catalog links and canonical checklist sitemap; `scripts/sync_domain_site.mjs` advertises it in domain-root robots.txt. Keep title/description/canonical/social metadata and JSON-LD unique and source-accurate. Preserve published content in static HTML, avoid invented rich-result claims or release dates, and run `node scripts/verify_seo.mjs` after every build.

# Dedicated official imports

Refresh the Panini National Silver Packs PDF with `scripts/import_panini_national.py` using the bundled pdfplumber Python runtime. Its physical-column parser preserves every printed card number and numbering specification. The generic catalog importer must preserve `panini-pdf` imports; do not replace them with generic PDF text extraction. Run this dedicated refresh when checking official source revisions. Also refresh the Soccer Player of the Day source with `scripts/import_panini_soccer_pod.py`; it uses its own physical-column and published-country alignment checks. Both dedicated parsers use the preserved `panini-pdf` import kind.

# Shared research views

Generate research data and revision snapshots through `scripts/build_research.mjs`, invoked by the shared page generator. Preserve `data/revision-history.json`; unchanged source fingerprints must not create revision events. Never reconstruct unobserved historical changes. Keep global name search, pack-format comparisons and parallel ladders in `research.js` and the shared template. Preserve source units and numbering qualifiers. Run `node scripts/verify_research.mjs` alongside the existing checks before publishing research changes.

Refresh the 2026 Topps Chrome Formula 1 ruled PDF with `scripts/import_topps_f1_2026.py` using the bundled pdfplumber runtime. Preserve its `topps-grid-pdf` import kind in generic refreshes. Blank Name cells are official source values; do not fill them with inferred players. Product-page numbering and box contents are not pack odds.

Refresh 2026 Topps Midnight Football with `scripts/import_topps_midnight_2026.py`. It reconciles the generic catalog import against physical player/team/rookie columns and preserves `topps-grid-pdf`. The October 12 date is a preorder date, not a verified release date; do not infer unpublished odds or parallel specifications.
