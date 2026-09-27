# ClubATX consolidated player analytics

Read this reference when Veo exposes player-level statistics and the user asks to persist them.

## Canonical destination

- Store every valid source player row in `public.fixture_player_analytics`. The retired `fixture_player_match_stats` and `fixture_player_playing_time` tables must never be used.
- One row is identified by `(fixture_id, division_team_id, source, jersey_number)`. Keep the same jersey on opposing fixture sides as two distinct rows.
- A complete import passes the full replacement set for one fixture and source to `public.save_fixture_performance`; the function deletes and replaces that fixture/source set atomically with the match payload and official fixture result.
- Do not write this table directly. Do not pass a partial player array. Use `p_players = null` when player analytics are outside the requested write so existing rows remain unchanged. An empty array clears the source set and therefore requires explicit destructive confirmation.
- Unresolved rows are first-class analytics rows. Preserve them with both `fixture_lineup_id` and `athlete_slug` set to `null`; never discard a row or attach it to another athlete merely because its jersey is unresolved.

## Identity and link columns

Populate these columns from confirmed fixture context and the verified Veo source:

| Meaning | Database field | Rule |
| --- | --- | --- |
| ClubATX fixture side | `division_team_id` | Use the confirmed fixture home or away `division_team_id`, never a Veo ID or team-name lookup. |
| source | `source` | Use a short lower-snake-case value such as `veo`. |
| jersey | `jersey_number` | Required integer from 0 through 99. |
| Veo team label | `source_team` | Preserve the verified source label; use null only when unavailable. |
| Veo player ID | `source_player_id` | Preserve a stable source ID when the response supplies one; otherwise null. |
| Veo player name | `source_player_name` | Preserve a trustworthy source name when supplied; otherwise null. Do not substitute the ClubATX athlete name. |
| confirmed lineup row | `fixture_lineup_id` | Use the exact confirmed `fixture_lineups.id`; otherwise null. |
| confirmed athlete | `athlete_slug` | Use the slug on that exact confirmed lineup row; otherwise null. It must be null whenever `fixture_lineup_id` is null. |

The link pair must either both be supplied or both be null. A jersey match alone does not authorize a link.

## Source-field mapping

Copy values only from a verified per-player source. Do not calculate player metrics from team totals or `key_events`.

| Veo meaning | Database field | Rule |
| --- | --- | --- |
| exact aggregate seconds | `played_seconds` | Preserve verified aggregate `secondsPlayed`; follow [clubatx-playing-time.md](clubatx-playing-time.md). |
| tracked minutes | `tracked_minutes` | Store the displayed integer minutes; do not convert it to exact seconds. |
| distance in miles | `distance_miles` | Preserve the displayed numeric value and unit. |
| average speed in mph | `average_speed_mph` | Preserve the displayed numeric value and unit. |
| top speed in mph | `top_speed_mph` | Preserve the displayed numeric value and unit. |
| sprints | `sprints` | Copy the displayed count. |
| high-intensity runs | `high_intensity_runs` | Copy the displayed count. |
| total events | `total_events` | Copy the source total; do not sum other fields. |
| goals | `goals` | Copy the player-table value. |
| assists | `assists` | Copy the player-table value. |
| goal involvements | `goal_involvements` | Copy the source value; do not recompute goals plus assists. |
| conversion rate | `conversion_rate_percent` | Store the displayed 0-through-100 percentage, not a fraction. |
| shots | `shots` | Copy the displayed count; keep distinct from total attempts. |
| total attempts | `total_attempts` | Copy the source count; do not derive it from shots. |
| tackles | `tackles` | Copy the displayed count. |
| corners | `corners` | Copy the displayed count. |
| free kicks | `free_kicks` | Copy the displayed count. |
| throw-ins | `throw_ins` | Copy the displayed count. |
| fouls | `fouls` | Copy the displayed count. |
| penalty kicks | `penalty_kicks` | Copy the displayed count. |
| goal kicks | `goal_kicks` | Copy the displayed count. |
| passes | `passes` | Copy only from a verified player source; otherwise null. |
| completed passes | `completed_passes` | Copy only from a verified player source; otherwise null. |
| pass success | `pass_success_rate_percent` | Store a verified displayed 0-through-100 percentage; otherwise null. |
| dribbles | `dribbles` | Copy only from a verified player source; otherwise null. |
| interceptions | `interceptions` | Copy only from a verified player source; otherwise null. |
| saves | `saves` | Copy only from a verified player source; otherwise null. |

Missing nullable source fields remain null. Never use zero as a missing-value placeholder. If a field required by the verified rendered player table is missing or non-numeric for only some rows, disclose the limitation and stop that player-data import rather than creating inconsistent rows.

## Resolve the athlete link

1. Determine the confirmed canonical fixture side that owns each source row.
2. Query `public.fixture_lineups` using the confirmed `fixture_id`, that side's `division_team_id`, and `jersey_number`. Select `id`, `athlete_slug`, `player_name`, and `jersey_number`.
3. Zero matches, duplicate matches, or a null athlete slug means unresolved. A unique linked row is only a candidate until the user confirms using the current fixture lineup.
4. For a confirmed candidate, copy the lineup `id` and its exact `athlete_slug`. Do not search another fixture side or use a similarly named athlete as a substitute.
5. If the user changes a lineup or jersey assignment, discard cached results, query the lineup again, rebuild every affected row, and obtain a fresh write confirmation.

## Consolidate and validate

Merge player-stat and exact-time source records by confirmed `division_team_id` and `jersey_number` before saving. Each output object contains the full identity/link fields plus every applicable metric column exactly once. Never merge the same jersey across opposing sides.

Validate before preview:

- the array contains every valid source player row for the fixture/source replacement set;
- `(division_team_id, jersey_number)` is unique within the array;
- each division team is exactly the fixture's confirmed home or away team;
- jersey, whole-second, minute, and count fields are non-negative integers within database bounds;
- decimal fields are finite, non-negative, and use no more than two decimal places;
- both link fields are null or both exactly match the confirmed lineup row;
- no metric was recalculated from team analytics or the event feed.

Preview total, linked, and unresolved row counts; every identity and link; exact seconds with rounded display minutes; units; and all stored metrics. The final database write and verification procedure is in [clubatx-supabase.md](clubatx-supabase.md).
