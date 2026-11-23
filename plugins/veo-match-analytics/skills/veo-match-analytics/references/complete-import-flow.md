# Complete Veo import flow

User requests for a complete import include all available match analytics. The items below are mandatory coverage categories, not a fixed list limiting future Veo modules. Re-inventory the actual report, selectors, periods, player attributes, charts, and observed match responses each run. Apply the explicit passing-network exception: only directed source connections with completed-pass counts greater than 3 are persisted; the complete unfiltered network belongs only in the local audit.

## 1. Resolve and audit

Validate the exact Veo match identity and resolve the ClubATX fixture read-only. Audit current fixture, complete payload including extensions, all player analytics, and all fixture events. Back them up before replacement. Confirm fixture, both side mappings, official score, and unresolved athlete assignments once per changed decision set. Reuse unchanged confirmations and user corrections. Do not ask users to find IDs available from the connected data.

## 2. Capture every available source scope

| Coverage | Capture | Persistence destination |
| --- | --- | --- |
| Match and team statistics | Both canonical teams, full match and available period breakdowns, source values, labels, precision, timing, score, and limitations | Canonical `match` / `teams` fields; additional verified breakdowns in `source.analytics_modules` |
| Veo AI discoveries | All five current sections: Overview, Distribution, Attacking, Defending, Physical; every heading and bullet, plus any newly discovered cards and accessible scopes | Top-level `analysis_reports`: preserve original `source_blocks`, personalize displayed `blocks` with confirmed team-specific player names, retain AI attribution and provenance |
| Shot maps | Verified marker IDs, coordinates, normalized orientation, goals versus shots, source jersey, athlete link, period and timestamps; prevent duplicate goal markers | `teams.<canonical>.shot_map` using the inspected consumer contract; preserve raw coordinate provenance |
| Passing networks | Source average positions and directed completed-pass counts; retain only edges with counts ≥4 and their required nodes | `teams.<canonical>.passing_network`, including auditable counts and direction |
| Play-by-play | Complete verified source feed, exact match/video times, cumulative minutes, source IDs, team and confirmed athlete links; supported relational projections and exact skipped reasons | `key_events` plus the complete approved `fixture_events` projection |
| All individual statistics | Enable every available attribute (currently 33), verify header/cell inventory, preserve source rows and jersey aliases, exact aggregate seconds separately from rounded minutes | Complete `fixture_player_analytics` replacement through the shared function; typed fields must support every attribute |
| Other charts and modules | Pass location/direction/strings, possession location, average positions, heat maps, physical and speed-zone charts, other accessible module and period data, definitions and units | Consumer-specific normalized fields when implemented, plus complete verified match-scoped module data in `source.analytics_modules` |

`source` is an optional JSONB payload extension already supported by the shared SQL save path. Use a documented object with `provider`, `match_id`, exact `report_url`, `captured_at`, `coverage`, and `analytics_modules`. Each additional module carries `module`, canonical `team` or null, `period`, labels/units, verified source data, and observation provenance. Preserve supported existing source fields when updating; explicitly reconcile stale extraction summaries rather than carrying misleading coverage. Never include cookies, headers, credentials, account responses, or unrelated data. Do not duplicate unfiltered passing-network edges in this extension; its stored network must follow the >3 rule. A module without a reliable structured representation can retain verified rendered labels/cells or chart primitives here, with their limitations, rather than silently vanishing from the database. Local exports alone are not persistence.

Do not assume a UI module exists for every persisted additional chart. State UI support separately; a missing renderer must be disclosed, not described as a displayed pitch/map. Inspect actual save and read paths before adding extensions: the canonical API parser may reject them even when the shared SQL function accepts JSONB. Never run a complete extended payload through a stripping parser. Use the verified complete shared-function transaction, or finish a separately authorized API capability upgrade.

## 3. Completeness gate before preview

Maintain an independently captured coverage manifest. Every available module/attribute must have a verified intended database path and exact expected normalized value; inaccessible modules need explicit observed reasons. `pending`, missing paths, silently dropped fields, and `export only` block a claim of complete import. Distinguish true empty/zero source results from unavailable data. Never infer missing source values to satisfy this gate. Run `${PLUGIN_ROOT}/scripts/validate_capture.py MANIFEST.json BUNDLE.json` against the intended normalized bundle; paths can address `/payload/...` or `/players/...`. The manifest entries have `module`, `status` (`captured` or `unavailable`), `source_url`, and either `path` plus `expected`, or a nonempty `reason`. Retain this manifest locally and its compact coverage outcome in the saved `source.coverage`.

Also run the extension preservation check and passing threshold check. Compare per-module counts and exact values, all original AI bullet blocks plus verified name substitutions in displayed blocks, marker identities/outcomes, every player column and row, full feed coverage and relational projection constraints. Verify chronology used for passing playback; raw feed wire order can be grouped by type and must remain independently archived. Preserve verified data over source disagreements and disclose them.

## 4. One concrete write preview

Present a compact coverage table: module, captured count/scope, intended destination, and any limitation. Show every changed mapping, score, half duration, source row/athlete count, all individual fields, AI section/bullet counts, shot markers/goals, retained/excluded passing connections under >3, complete feed count, old/new relational event counts, supported/skipped event types, URL pre-roll, and finalization state. Explain destructive event replacement and preserve unrelated data. Prepare the exact normalized artifact and guarded SQL before asking for final confirmation. Require one confirmation for the changed write set; do not reconfirm unchanged fixture, side, score, or athlete decisions.

## 5. Atomic save

After authorization use one transaction with the complete supported payload and full intended player set, one shared save-function call, approved relational replacement if applicable, timing/finalization updates if in scope, concurrency guards, and pre-commit equality assertions. A narrow repair changes only the requested fields; do not rebuild or delete unrelated data. Run schema upgrades as a separate explicitly authorized phase when required. No silent fallback to partial persistence.

## 6. Readback and actual fixture verification

Compare the complete saved payload against the exact intended JSON, every saved player value/link and exact seconds, the duplicate-preserving event set, score and timing/finalization fields. Re-run the coverage and preservation gates using readback values. Verify ClubATX team statistics, all five AI sections and bullets with confirmed player names under Match reports, passing-network pitch and Play progress, and play-by-play/video links through the actual page. Verify the shot-map renderer if present; otherwise explicitly report data saved and UI unsupported/unverified. Confirm Veo's applied all-column setting when requested. Report each available section as saved only after readback. Do not claim “everything imported” with unexplained unavailable, pending, or export-only categories.
