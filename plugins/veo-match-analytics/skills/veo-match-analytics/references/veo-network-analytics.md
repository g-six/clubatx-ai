# Veo match, team, and player response extraction

Read this reference whenever match metadata, team statistics, or player statistics are requested from a Veo match, and before persisting those analytics.

## Observe requests by UI action

Use the Browser plugin's supported request/network inspection in the exact authenticated match tab. Start observation before triggering analytics so each response can be associated with the action that caused it.

1. If observation began after page load, reload the exact user-supplied match URL once. Capture the Fetch/XHR requests produced by the base match page.
2. Open `Stats`, wait for it to settle, and capture newly observed Fetch/XHR requests.
3. Open `Player Stats Overview` with `View table`, wait for the table to settle, and capture newly observed Fetch/XHR requests.
4. Open another read-only analytics module only when needed, and inspect the requests added by that specific action before moving on.

Record the request URL, method, status, response content type, triggering UI action, and response body when the supported browser surface exposes them. Ignore telemetry, feature-flag, advertisement, configuration, and user-account responses unless they directly contain the requested match analytics. Do not guess endpoints or iterate URL variants.

## Identify response roles from content

Endpoint names are not stable. Classify candidates from the response payload and verify their relationship to the current match.

### Match response

A trusted match response must identify the current recording or match through the page slug, a stable identifier also exposed by the page, or a unique combination of title, date, and both teams. It should contain match-level fields such as the title, team identities, recording duration, date, score state, processing state, or available analytics modules. Do not treat a playback-position scoreboard as a final result.

When the source exposes side-confirmation state or per-period own-side orientation, preserve it as mapping evidence. If the user reports that match sides were corrected, reload the exact analysis page, re-read that current evidence, and invalidate all previously mapped team, event, player, and division-team values. Never repair only the displayed team names while leaving metrics or event ownership on the old sides.

### Team-stat response

A trusted team-stat response must:

- represent both visible Veo teams or expose team IDs that map unambiguously to them;
- contain a collection of labeled metrics or metric keys and values for each team;
- match the rendered `Stats` panel on both team identities and at least three available metrics, including their side assignment;
- preserve distinctions such as shots versus total attempts, and counts versus percentages.

Use the verified team-stat response as the primary source for every team metric it contains. Use the rendered labels and units to interpret response fields and confirm team identity, side assignment, and metric meaning. A rendered-value disagreement does not override the response: preserve both values in the audit and persist the team-stat response value.

For a metric absent from the verified team-stat response, use the corresponding value from a verified match-details response when available. Apply this fallback metric by metric; do not replace the whole team-stat dataset with match-details. If both responses contain the same metric and disagree, persist the team-stat value and record the match-details value in the audit and write preview. Do not average values or force agreement. If neither response supplies a required metric, use a clearly labeled rendered value only when the relevant analytics panel displays it; otherwise mark the field unavailable and follow the persistence schema's missing-data rules.

### Player-stat response

A trusted player-stat response must:

- belong to the current match and the team shown in `Player Stats Overview`;
- contain an ordered or uniquely keyed collection of players or detected jerseys;
- expose values that map to the current rendered column headers;
- match at least three rendered player rows on jersey or player identity and at least three metrics per checked row when that many values are available.

Use the response to extract the complete player collection only after these checks pass. Preserve the rendered table's labels, units, displayed precision, column order, and missing-value semantics. Do not turn a missing field into zero, infer a player name from a jersey, or recalculate one metric from another. If the response contains additional undocumented fields that are not represented in the current table or persistence schema, report them separately rather than inserting them into a known column.

### Exact playing-time response

A trusted exact playing-time response must:

- identify the current match through a stable match identifier correlated with the match page;
- identify the player-stat table's confirmed Veo team, or expose a team identifier that maps unambiguously to it;
- contain unique non-negative integer jersey numbers and non-negative integer `secondsPlayed` values;
- expose an aggregate total row for each jersey when it also exposes period or drill rows; and
- satisfy `Math.round(secondsPlayed / 60)` for at least three rendered tracked-minute rows, and preferably every available row.

Physical-metrics responses may contain period rows plus an aggregate row such as `drill: "ALL"`. Treat the aggregate row as the exact match total. Never add the aggregate to its component period rows, and never multiply the rendered rounded minutes by 60. If there is no clearly identified aggregate total, keep the period rows separate and stop before a playing-time write rather than guessing how they combine.

Exact seconds and rendered tracked minutes are related verification signals but different columns in the same consolidated row. Preserve the exact response seconds as `fixture_player_analytics.played_seconds` and the independently displayed integer minutes as `fixture_player_analytics.tracked_minutes`; never derive one from the other.

## Cross-source handling

Keep match metadata, team statistics, displayed player statistics, exact playing time, and events as separate source scopes even when one response contains more than one scope. Correlate stable IDs across responses, but do not derive one dataset from another.

- For team metrics, prefer the verified team-stat response; use verified match-details only for metrics missing from that response. Preserve and report conflicts, with the team-stat response winning overlaps.
- Keep the rendered panel authoritative for human-facing labels, units, and displayed precision. Use rendered values to interpret and cross-check sources, not to silently overwrite a verified team-stat value.
- Never replace team or player metrics with aggregates from the event feed.
- Preserve processing, reduced-accuracy, subscription, or missing-data warnings from either source.

If the browser surface exposes request URLs but not response bodies, report that raw response verification was unavailable and extract the rendered tables instead. Do not claim that a response was inspected when only its URL was visible.
