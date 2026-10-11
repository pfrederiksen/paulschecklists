# Checklist experience

The first Allen & Ginter page defines the experience for every set. All set pages must be generated with `templates/set-page.mjs` through `node scripts/generate_source_pages.mjs`; do not create separate page shells or manufacturer-specific navigation layouts. Featured content lives in `templates/featured-sets.json`.

Keep the same header, hero, statistics, insights, Cards / Parallels & pack odds tabs, search, subset/team/pack-format filters, rookie control, sorting, reset, CSV export, card family details, family odds tables, pagination, and source explanation. Disable controls with unavailable source fields rather than changing their position. Keep manufacturer-specific published specifications inside these shared views. Preserve official columns in expanded card details. Do not invent teams, rookie flags, pack formats, category odds, print runs, or parallel eligibility.

For new sets and source updates, run `node scripts/verify_set_template.mjs`, `node scripts/verify_source_pages.mjs`, `node scripts/verify_ui.mjs`, `node scripts/verify_bowman.mjs`, and `node scripts/verify_catalog.mjs` after generating/building. Add new data through adapters and the shared template rather than introducing a new visual or interaction format.
