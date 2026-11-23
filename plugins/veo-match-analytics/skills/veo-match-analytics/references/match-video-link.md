# Match Video must open the raw Veo MP4

## Separate three URL roles

- Navigation/source identity: keep the original user-supplied `https://app.veo.co/...` string unchanged in `payload.source.report_url`. Report objects retain their own `source_url`. Do not rewrite or overwrite these with a CDN URL.
- Fixture Match Video: `public.fixtures.video_url` and `payload.source.raw_video_url` contain the verified HTTPS MP4 source of the exact match's standard player, without any fragment. Keep its host, path, case, percent-encoding, and query string exactly as observed. The fixture link opens the recording from its normal start.
- Event playback: each `fixture_events.video_url` uses that same raw MP4 plus `#t=<max(exact_video_seconds - confirmed_pre_roll_seconds, 0)>`. Keep existing pre-roll and exact source timestamps unchanged when correcting only Match Video.

## Observe and validate

Use the supported browser inspection for the authenticated match tab: the standard player's loaded `video.currentSrc` / `source.src`, or its observed matching media response. Follow the raw-recording checks in [veo-network-events.md](veo-network-events.md). Match the recording to the exact source match, standard player, and verified recording metadata; do not select highlight clips or alternative cameras by URL order. Never guess a CDN path, derive one from the UUID, or request account credentials. Do not use Download or download the full recording for this check.

Run `${PLUGIN_ROOT}/scripts/match_video_link.py REPORT_URL OBSERVED_MP4_URL` after source verification. The helper validates URL roles, strips only the MP4 fragment, and returns `fixture_video_url` and the separate `source` metadata. It is a syntax/normalization guard, not proof that a URL belongs to a match; browser source identity checks remain required. Preserve signed query parameters exactly; if the observed source is expired or unavailable, re-observe a valid match source and disclose the blocker rather than falling back to a report URL, HLS, or blob URL.

## Preview, save, and read back

Include current and proposed fixture URL, exact report source URL, and observed recording identity in the final preview. Use the raw MP4 as `p_video_url` in `save_fixture_performance`, in the same atomic full import. Merge the `source` metadata with supported existing source fields instead of replacing unrelated metadata. Include both URL roles in the completeness manifest and readback equality checks.

For a separately requested fixture-link correction, lock and audit the fixture and payload, guard the expected old URL and payload state, call the shared function once with `p_players = null`, and pass either the preserved payload with only the source URL metadata merged or `p_match_stats = null` if provenance is already complete. Preserve official scores, clock/finalization, all report sections and player names, charts, player analytics, key events, and every event URL. No event or player replacement is needed. Assert exact unrelated-data equality before commit.

After commit read back `fixtures.video_url` and source metadata. Open the actual fixture page and inspect Match Video's link target; require the exact MP4 without a timestamp fragment and verify that it opens the same recording in the browser's native video player. Do not claim the fixture link was fixed merely because event video links already point to MP4.
