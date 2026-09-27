# ClubATX exact playing-time persistence

Read this reference when a verified Veo response exposes exact player `secondsPlayed` and persistence is requested.

## Destination and source rules

- Store exact seconds in the `played_seconds` column of the player's consolidated `public.fixture_player_analytics` row. Never use the retired `fixture_player_playing_time` table and never put playing time in `fixture_match_stats.payload`.
- Merge exact time with the same fixture-side/source/jersey row that holds displayed player metrics. If only exact time is available, keep unavailable nullable metrics null; never invent zeros.
- Preserve the verified aggregate `secondsPlayed` integer exactly. The UI may display `Math.round(played_seconds / 60)`, but the database value remains exact seconds.
- When the response contains period rows and an aggregate row such as `drill: "ALL"`, use the aggregate row only. Never add the aggregate to component rows.
- Never derive exact seconds by multiplying rendered tracked minutes by 60, and never replace the separate displayed `tracked_minutes` value with a seconds conversion.

## Resolve and consolidate

1. Determine the confirmed canonical fixture side and its `division_team_id` for each exact-time response.
2. Require one unique non-negative integer jersey number per aggregate source row.
3. Merge the exact time into the player object with the same confirmed `division_team_id` and `jersey_number`.
4. Refresh `public.fixture_lineups` for that fixture, division team, and jersey. A unique linked row is a candidate until the user confirms it.
5. Store a confirmed link as the exact `fixture_lineup_id` and `athlete_slug` pair. Store both fields as null for zero matches, duplicate matches, null athlete slugs, or a user-declined link. The analytics row is still persisted.
6. If the user changes a lineup or jersey assignment, discard cached results and rebuild the consolidated replacement set before obtaining a new write confirmation.

## Validate and preview

Require each `played_seconds` value to be a non-negative integer no greater than 86400. Verify the response against the rendered table with `Math.round(played_seconds / 60)` for at least three jerseys and preferably every row. A mismatch is a data-quality issue: show both values and stop the affected player-data write.

Preview the source team, total player-row count, linked and unresolved counts, every link pair, exact seconds, rounded display minutes, and whether displayed player metrics were merged into the same rows.

## Save and verify

Follow [clubatx-supabase.md](clubatx-supabase.md). Pass the complete player replacement array to `public.save_fixture_performance`; do not upsert playing time separately. After the transaction, read `public.fixture_player_analytics` by the confirmed fixture and source and verify every exact `played_seconds`, side, jersey, link pair, and row count. Report rounded minutes only as a display check.
