# ClubATX player-stat persistence

Read this reference only when Veo exposes `Player Stats Overview` and the user asks to persist it.

## Destination and availability

- Store player rows in `public.fixture_player_match_stats`; do not embed them in `fixture_match_stats.payload`.
- The compatible schema is introduced by `supabase/migrations/20260927035819_track_fixture_player_match_stats.sql`.
- Before preparing a write, query the catalog or table for availability. If the table is absent, stop and identify the migration; do not create or alter schema during an import.
- Each row is identified by `(fixture_id, fixture_lineup_id)` and is also unique by `(fixture_id, athlete_slug)`.
- The composite foreign key `(fixture_id, fixture_lineup_id, athlete_slug)` requires the saved athlete to be the athlete already linked to that exact fixture-lineup row.
- Omitted rows are preserved. Do not delete prior player statistics unless the user explicitly asks to replace or remove them and confirms the destructive scope.

## Source-field mapping

Use the rendered column labels and displayed units. Normalize only to these database names:

| Veo meaning | Database column | Rule |
| --- | --- | --- |
| tracked minutes | `tracked_minutes` | Store the displayed integer minutes; do not convert to seconds or infer exact playing time. |
| distance in miles | `distance_miles` | Preserve the displayed numeric value. |
| average speed in mph | `average_speed_mph` | Preserve the displayed numeric value. |
| top speed in mph | `top_speed_mph` | Preserve the displayed numeric value. |
| sprints | `sprints` | Copy the displayed count. |
| high-intensity runs | `high_intensity_runs` | Copy the displayed count. |
| total events | `total_events` | Copy the displayed count; do not sum other columns. |
| goals | `goals` | Copy the displayed count. |
| assists | `assists` | Copy the displayed count. |
| goal involvements | `goal_involvements` | Copy the displayed count; do not recompute goals plus assists. |
| conversion rate | `conversion_rate_percent` | Store the displayed percentage as 0 through 100, not as a 0-through-1 fraction. |
| shots | `shots` | Copy the displayed count; keep distinct from total attempts. |
| total attempts | `total_attempts` | Copy the displayed count; do not derive it from shots or the event feed. |
| tackles | `tackles` | Copy the displayed count. |
| corners | `corners` | Copy the displayed count. |
| free kicks | `free_kicks` | Copy the displayed count. |
| throw-ins | `throw_ins` | Copy the displayed count. |
| fouls | `fouls` | Copy the displayed count. |
| penalty kicks | `penalty_kicks` | Copy the displayed count. |
| goal kicks | `goal_kicks` | Copy the displayed count. |

The current table requires all metric columns. If Veo omits a required column or displays a non-numeric placeholder, do not silently store zero. Report the affected rows and stop the player-stat write while leaving any separately confirmed match-payload write unchanged.

## Resolve the athlete link

1. Determine which confirmed canonical team owns the player table. Never assume it is the database home team merely because Veo shows it first.
2. Require a non-negative integer jersey number for every row to persist. A displayed name without a jersey is insufficient for this schema.
3. Query `public.fixture_lineups` using all three of: confirmed `fixture_id`, the corresponding fixture-side `division_team_id`, and `jersey_number`. Select `id`, `athlete_slug`, `player_name`, and `jersey_number`.
4. Zero matches means the row is unresolved. Multiple matches mean the jersey is ambiguous. A single row with null `athlete_slug` is unlinked. Present these states; never choose another team, a similarly named player, or an athlete search result as a substitute.
5. Confirm that the user accepts the current lineup links for these player rows. Then use the lineup row's `id` as `fixture_lineup_id` and its exact `athlete_slug` as `athlete_slug`.
6. If the user changes jersey assignments or athlete links, discard all cached lineup results and repeat the query before rebuilding the write set.

Player-stat rows with no confirmed link cannot satisfy the foreign key. Skip and report them. This does not require removing the same jersey's unlinked events from `fixture_match_stats.payload`; event JSON permits `athlete_slug: null`.

## Validate and preview

Before the write, verify:

- every source row was copied cell-for-cell exactly once;
- jerseys are unique within the source table's team scope;
- each write row resolves to exactly one current lineup row and non-null athlete slug;
- integer fields are non-negative integers; tracked minutes are at most 1440;
- decimal fields are finite and non-negative, use no more than two decimals, speeds and percentages are at most 100, and distance is at most 1000;
- `source` is a short lower-snake-case identifier such as `veo`;
- no player-table metric was recalculated from team statistics or `key_events`.

Preview the extracted row count, linked write count, skipped rows with reasons, jersey-to-athlete mappings, units, and all displayed metrics. A confirmation made before a lineup refresh or data correction is stale and cannot authorize the revised rows.

## Save and verify

Use the Supabase SQL connector. Prefer one statement for the confirmed match payload, official score, and player rows so a failure rolls back the whole requested import. Construct player values from the validated rows and upsert with:

```sql
insert into public.fixture_player_match_stats (
  fixture_id,
  fixture_lineup_id,
  athlete_slug,
  source,
  tracked_minutes,
  distance_miles,
  average_speed_mph,
  top_speed_mph,
  sprints,
  high_intensity_runs,
  total_events,
  goals,
  assists,
  goal_involvements,
  conversion_rate_percent,
  shots,
  total_attempts,
  tackles,
  corners,
  free_kicks,
  throw_ins,
  fouls,
  penalty_kicks,
  goal_kicks,
  updated_at
)
values (...)
on conflict (fixture_id, fixture_lineup_id) do update
set
  athlete_slug = excluded.athlete_slug,
  source = excluded.source,
  tracked_minutes = excluded.tracked_minutes,
  distance_miles = excluded.distance_miles,
  average_speed_mph = excluded.average_speed_mph,
  top_speed_mph = excluded.top_speed_mph,
  sprints = excluded.sprints,
  high_intensity_runs = excluded.high_intensity_runs,
  total_events = excluded.total_events,
  goals = excluded.goals,
  assists = excluded.assists,
  goal_involvements = excluded.goal_involvements,
  conversion_rate_percent = excluded.conversion_rate_percent,
  shots = excluded.shots,
  total_attempts = excluded.total_attempts,
  tackles = excluded.tackles,
  corners = excluded.corners,
  free_kicks = excluded.free_kicks,
  throw_ins = excluded.throw_ins,
  fouls = excluded.fouls,
  penalty_kicks = excluded.penalty_kicks,
  goal_kicks = excluded.goal_kicks,
  updated_at = now();
```

Read back only the confirmed fixture's saved rows and join them to `fixture_lineups` on the complete composite identity. Verify the returned count equals the linked write count and compare every athlete slug and metric to the intended source value. Database numerics may serialize as strings; compare exact numeric values without introducing additional rounding. Report skipped unlinked rows separately and never count them as saved.
